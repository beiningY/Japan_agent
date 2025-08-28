import queue
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple
from concurrent.futures import Future

# 全局请求队列
# maxsize=0 表示队列大小无限制
request_queue = queue.Queue(maxsize=0)

# 停止所有工作线程的事件标志
stop_event = threading.Event()

# 存储每个请求结果的字典，通过请求ID索引
# 注意：在实际生产环境中，你可能需要一个更健壮的机制来存储和检索结果，
# 例如一个共享内存、数据库或专门的结果队列
results_storage: Dict[str, Any] = {}

# 存储异常，便于调用方获知错误
errors_storage: Dict[str, BaseException] = {}

# 当前运行状态
_workers: List[threading.Thread] = []
_running_lock = threading.Lock()

class RAGWorker(threading.Thread):
    """
    RAG 工作线程，负责从队列中取出请求并执行 RAG 推理。
    """
    def __init__(self, worker_id):
        super().__init__()
        self.worker_id = worker_id
        self.name = f"RAG-Worker-{worker_id}"
        print(f"初始化 {self.name}")

    def run(self):
        """
        工作线程的执行逻辑。
        """
        print(f"{self.name} 启动。")
        while not stop_event.is_set():
            try:
                # 从队列中获取任务，如果队列为空，会阻塞直到有新任务
                # timeout=1 可以让线程每隔一秒检查 stop_event
                request_data = request_queue.get(timeout=1)
            except queue.Empty:
                # 队列为空，线程会继续循环检查 stop_event
                continue

            try:
                request_id = request_data['request_id']
                task_callable: Callable[..., Any] = request_data['callable']
                task_args: Tuple[Any, ...] = request_data.get('args', ())
                task_kwargs: Dict[str, Any] = request_data.get('kwargs', {})
                future: Optional[Future] = request_data.get('future')

                print(f"{self.name} 正在处理请求 ID: {request_id}")

                # 执行实际的任务逻辑（例如：RAG 检索/推理）
                result = task_callable(*task_args, **task_kwargs)
                print(f"{self.name} 完成请求 ID: {request_id}")

                # 将结果存储起来，以便主服务可以检索
                results_storage[request_id] = result
                if future is not None and not future.done():
                    future.set_result(result)

            except Exception as e:
                request_id = request_data.get('request_id')
                errors_storage[request_id] = e
                future = request_data.get('future')
                if future is not None and not future.done():
                    future.set_exception(e)
                print(f"Error in {self.name}: {e}")
                # 在实际应用中，你可能需要更详细的错误处理和日志记录
            finally:
                # 标记任务完成，通知队列可以处理下一个任务
                request_queue.task_done()

        print(f"{self.name} 停止。")

def start_rag_service(num_workers: int = 1):
    """
    启动 RAG 服务，包括创建并启动指定数量的工作线程。
    """
    global _workers
    with _running_lock:
        if _workers:
            print("RAG 服务已在运行，跳过重复启动。")
            return _workers
        print(f"正在启动 RAG 服务，将创建 {num_workers} 个工作线程...")
        for i in range(max(1, num_workers)):
            worker = RAGWorker(i + 1)
            worker.daemon = True # 将工作线程设置为守护线程，主线程退出时它们也会退出
            worker.start()
            _workers.append(worker)
        print("RAG 服务启动完毕。")
        return _workers

def stop_rag_service(workers: Optional[List[threading.Thread]] = None):
    """
    停止 RAG 服务和所有工作线程。
    """
    print("正在停止 RAG 服务...")
    stop_event.set() # 设置停止事件，通知所有工作线程退出循环
    global _workers
    if workers is None:
        workers = _workers
    for worker in list(workers or []):
        try:
            worker.join()
        except Exception:
            pass
    _workers.clear()
    print("RAG 服务已停止。")

def is_running() -> bool:
    """检查队列服务是否在运行"""
    return any(w.is_alive() for w in _workers)

def submit_task(task_callable: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
    """
    提交一个通用任务到队列（FIFO）。
    注意：task_callable 应该是线程安全的，并且可以在工作线程中执行。
    """
    request_id = str(uuid.uuid4())
    request_data = {
        'request_id': request_id,
        'callable': task_callable,
        'args': args,
        'kwargs': kwargs,
    }
    print(f"提交任务 ID: {request_id} 到队列。")
    request_queue.put(request_data)
    return request_id

def submit_task_future(task_callable: Callable[..., Any], *args: Any, **kwargs: Any) -> Tuple[str, Future]:
    """
    提交一个通用任务到队列，并返回 (request_id, future)。
    由工作线程在完成后设置 future 的结果或异常。
    """
    request_id = str(uuid.uuid4())
    future: Future = Future()
    request_data = {
        'request_id': request_id,
        'callable': task_callable,
        'args': args,
        'kwargs': kwargs,
        'future': future,
    }
    print(f"提交任务(带Future) ID: {request_id} 到队列。")
    request_queue.put(request_data)
    return request_id, future

def get_task_result(request_id: str, timeout: Optional[float] = None) -> Any:
    """
    获取指定请求 ID 的任务结果。若发生异常，则抛出异常；若超时，抛出 TimeoutError。
    """
    start_time = time.time()
    while True:
        if request_id in results_storage:
            return results_storage.pop(request_id)
        if request_id in errors_storage:
            error = errors_storage.pop(request_id)
            raise error
        if timeout is not None and (time.time() - start_time) >= timeout:
            raise TimeoutError("Timeout: 结果未在指定时间内返回。")
        time.sleep(0.05)

def run_in_queue(task_callable: Callable[..., Any], *args: Any, timeout: Optional[float] = None, **kwargs: Any) -> Any:
    """
    便捷方法：提交任务并同步等待结果返回。
    """
    if not is_running():
        # 默认单线程以保证 GPU 推理串行化
        start_rag_service(num_workers=1)
    request_id, future = submit_task_future(task_callable, *args, **kwargs)
    return future.result(timeout=timeout)

def run_in_queue_async(task_callable: Callable[..., Any], *args: Any, **kwargs: Any) -> Tuple[str, Future]:
    """
    非阻塞提交：返回 (request_id, future)。调用方可在稍后 future.result() 或添加回调。
    """
    if not is_running():
        start_rag_service(num_workers=1)
    return submit_task_future(task_callable, *args, **kwargs)


# --- 服务主入口示例 ---
if __name__ == "__main__":
    # 简单自测：提交三个加法任务，验证 FIFO 串行执行
    print("\n--- 启动服务 ---")
    rag_workers = start_rag_service(num_workers=1)

    def add(a, b):
        time.sleep(0.2)
        return a + b

    ids = [submit_task(add, i, i+1) for i in range(3)]
    for rid in ids:
        print("结果:", get_task_result(rid))

    print("\n--- 等待所有队列任务完成 (可选) ---")
    request_queue.join()
    print("所有队列任务已处理完成。")

    print("\n--- 停止服务 ---")
    stop_rag_service(rag_workers)
    print("服务已完全关闭。")