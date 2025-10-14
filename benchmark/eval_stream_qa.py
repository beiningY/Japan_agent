import json
import logging
import os
import statistics
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests

try:
    import sseclient  # type: ignore
except Exception:  # pragma: no cover
    sseclient = None  # 下方会使用的惰性降级回退

# 固定默认参数，便于一键评估
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
URL = "http://127.0.0.1:5001/sse/stream_qa"
BENCHMARK_PATH = os.path.join(BASE_DIR, "南美白对虾问题集.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "results")
OUTPUT_JSON = os.path.join(OUTPUT_DIR, "stream_qa_eval.json")
AGENT_TYPE = "japan"
CONNECT_TIMEOUT_S = 10.0
HARD_TIMEOUT_S = 180.0

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def read_json_file(file_path: str) -> Any:
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_dir(path: str) -> None:
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)


def normalize_query_key(item: Dict[str, Any]) -> Optional[str]:
    # 规范化键名称（将诸如 "qu er y" 的异常键视为 "query"）
    if "query" in item and isinstance(item["query"], str):
        return item["query"].strip()
    for key in item.keys():
        if key.replace(" ", "").lower() == "query" and isinstance(item[key], str):
            return item[key].strip()
    return None


def default_config() -> Dict[str, Any]:
    # 对齐 tests/tests_requests.py::test_stream_qa() 中的配置
    return {
        "rag": {
            "collection_name": "japan_shrimp",
            "topk_single": 5,
            "topk_multi": 5,
        },
        "mode": "single",
        "single": {
            "temperature": 0.4,
            "system_prompt": (
                "你是数据获取与分析助手。你可以使用 retrieve 工具从知识库检索相关信息，"
                "或者按照顺序从数据库中获取相关数据，若使用read_sql_query，需要首先根据需求"
                "使用list_sql_tables，get_tables_schema对于数据库的表进行了解，然后再执行查询命令。"
                "最后根据检索到的真实数据来回答用户的问题。不要直接使用你自己的知识回答，"
                "必须基于工具返回的数据。回答中请明确引用来源（文件名/表名），并避免臆断。"
            ),
            "max_tokens": 10000,
        },
    }


def build_params(
    session_id: str,
    agent_type: str,
    query: str,
    config: Dict[str, Any],
) -> Dict[str, str]:
    return {
        "session_id": session_id,
        "agent_type": agent_type,
        "query": query,
        "config": json.dumps(config, ensure_ascii=False),
    }


def _iter_sse_events(response: requests.Response):
    # 若可用优先使用 sseclient 进行稳健解析；否则回退为逐行解析
    if sseclient is not None:
        client = sseclient.SSEClient(response)  # type: ignore
        for event in client.events():
            yield event.data
    else:  # pragma: no cover
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            if line.startswith("data: "):
                yield line[6:]


def eval_one_query(
    url: str,
    agent_type: str,
    query: str,
    config: Dict[str, Any],
    connect_timeout_s: float,
    hard_timeout_s: float,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    session_id = str(uuid.uuid4())
    logger.info(f"开始评估查询 | session_id={session_id} | query={query[:50]}...")
    params = build_params(session_id=session_id, agent_type=agent_type, query=query, config=config)

    # 时间指标采集
    batch_start = time.perf_counter()
    t_first_event: Optional[float] = None
    event_count = 0
    total_bytes = 0
    raw_events: List[Dict[str, Any]] = []
    answer_text: Optional[str] = None
    completed = False
    error_message: Optional[str] = None

    try:
        with requests.get(url, params=params, stream=True, timeout=(connect_timeout_s, None)) as resp:
            status_ok = resp.status_code == 200
            if not status_ok:
                logger.error(f"HTTP错误 | session_id={session_id} | status={resp.status_code}")
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")

            for data_str in _iter_sse_events(resp):
                now = time.perf_counter()
                if t_first_event is None:
                    t_first_event = now

                event_count += 1
                try:
                    total_bytes += len(data_str.encode("utf-8"))
                except Exception:
                    total_bytes += len(data_str)

                # 记录带相对时间偏移的原始事件
                raw_events.append({
                    "t_offset_s": round(now - batch_start, 6),
                    "data": data_str,
                })

                # 解析事件负载
                try:
                    payload = json.loads(data_str)
                    # 最终答案的数据结构来自 api/routes/qa_sse.py
                    data_field = payload.get("data", {}) if isinstance(payload, dict) else {}
                    if isinstance(data_field, dict) and data_field.get("status") == "completed":
                        answer_text = data_field.get("answer")
                        completed = True
                        logger.info(f"查询完成 | session_id={session_id} | events={event_count}")
                        break
                    if "error" in payload:
                        error_message = str(payload.get("error"))
                        logger.error(f"查询出错 | session_id={session_id} | error={error_message}")
                        break
                except json.JSONDecodeError:
                    # 非 JSON 事件可忽略解析，仅做原样存储
                    pass

                # 流式处理中执行硬超时检查
                if hard_timeout_s and (now - batch_start) > hard_timeout_s:
                    error_message = f"Timed out after {hard_timeout_s} seconds"
                    logger.warning(f"查询超时 | session_id={session_id} | timeout={hard_timeout_s}s")
                    break
    except Exception as e:
        error_message = str(e)
        logger.error(f"查询异常 | session_id={session_id} | exception={error_message}")

    end_time = time.perf_counter()
    latency_s = end_time - batch_start
    ttfb_s = (t_first_event - batch_start) if t_first_event is not None else None
    bytes_per_second = (total_bytes / latency_s) if latency_s > 0 else 0.0

    result = {
        "session_id": session_id,
        "query": query,
        "success": bool(completed and (error_message is None)),
        "error": error_message,
        "answer": answer_text,
        "event_count": event_count,
        "total_bytes": total_bytes,
        "latency_s": round(latency_s, 6),
        "ttfb_s": round(ttfb_s, 6) if ttfb_s is not None else None,
        "bytes_per_second": round(bytes_per_second, 6),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    
    logger.info(
        f"查询结果 | session_id={session_id} | success={result['success']} | "
        f"latency={latency_s:.3f}s | ttfb={ttfb_s:.3f}s | events={event_count}"
    )

    return result, raw_events


def write_json(path: str, payload: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def main() -> None:
    ensure_dir(OUTPUT_DIR)
    ensure_dir(BASE_DIR)

    logger.info("=" * 80)
    logger.info("开始流式问答评估")
    logger.info(f"URL: {URL}")
    logger.info(f"Agent类型: {AGENT_TYPE}")
    logger.info(f"基准文件: {BENCHMARK_PATH}")

    # 读取基准问题集
    data = read_json_file(BENCHMARK_PATH)
    if not isinstance(data, list):
        raise ValueError("Benchmark file must contain a JSON array of items")

    logger.info(f"加载了 {len(data)} 个问题")

    # 读取/生成运行配置
    cfg = default_config()

    run_start = time.perf_counter()
    per_query_results: List[Dict[str, Any]] = []

    # 默认按顺序执行以保证可复现性
    for idx, item in enumerate(data, 1):
        query_text = normalize_query_key(item)
        if not query_text:
            logger.warning(f"跳过无效问题 | index={idx}")
            continue
        qid = item.get("id")
        
        logger.info(f"进度: [{idx}/{len(data)}] | id={qid}")

        result, raw_events = eval_one_query(
            url=URL,
            agent_type=AGENT_TYPE,
            query=query_text,
            config=cfg,
            connect_timeout_s=CONNECT_TIMEOUT_S,
            hard_timeout_s=HARD_TIMEOUT_S,
        )

        result_with_id = {"id": qid, **result}
        per_query_results.append(result_with_id)

    run_end = time.perf_counter()
    wall_time_s = run_end - run_start

    # 汇总统计
    latencies = [r["latency_s"] for r in per_query_results if isinstance(r.get("latency_s"), (int, float))]
    successes = sum(1 for r in per_query_results if r.get("success"))
    total = len(per_query_results)
    avg_latency = statistics.mean(latencies) if latencies else None
    p50_latency = statistics.median(latencies) if latencies else None
    p90_latency = (statistics.quantiles(latencies, n=10)[8] if len(latencies) >= 10 else None) if latencies else None
    qps = (total / wall_time_s) if wall_time_s > 0 else None
    
    logger.info("=" * 80)
    logger.info("评估完成 - 汇总统计")
    logger.info(f"总耗时: {wall_time_s:.2f}s")
    logger.info(f"问题总数: {total}")
    logger.info(f"成功: {successes} | 失败: {total - successes}")
    logger.info(f"成功率: {(successes/total*100):.1f}%" if total > 0 else "N/A")
    logger.info(f"QPS: {qps:.3f}" if qps else "N/A")
    logger.info(f"平均延迟: {avg_latency:.3f}s" if avg_latency else "N/A")
    logger.info(f"P50延迟: {p50_latency:.3f}s" if p50_latency else "N/A")
    logger.info(f"P90延迟: {p90_latency:.3f}s" if p90_latency else "N/A")
    logger.info("=" * 80)

    output_payload = {
        "run": {
            "url": URL,
            "agent_type": AGENT_TYPE,
            "benchmark": os.path.abspath(BENCHMARK_PATH),
            "started_at": datetime.utcnow().isoformat() + "Z",
            "wall_time_s": round(wall_time_s, 6),
            "count": total,
            "successes": successes,
            "failures": total - successes,
            "qps": round(qps, 6) if qps is not None else None,
            "avg_latency_s": round(avg_latency, 6) if avg_latency is not None else None,
            "p50_latency_s": round(p50_latency, 6) if p50_latency is not None else None,
            "p90_latency_s": round(p90_latency, 6) if p90_latency is not None else None,
        },
        "queries": per_query_results,
    }

    write_json(OUTPUT_JSON, output_payload)
    logger.info(f"结果已保存: {OUTPUT_JSON}")
    print(f"Saved: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()


