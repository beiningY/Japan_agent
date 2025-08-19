import json
import datetime
import schedule
import time
import argparse
import logging
import requests
from dataprocess.clean_log import clean_log_file
from rag.camel_rag import RAG
from embeddings.japan_book_chunking import chunk_data_for_log

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("get_log")
logger.setLevel(logging.INFO)


#====================获取未添加的日志数据===========================
def extract_date_from_chunk_id(chunk_id):
    """从chunk_id中提取日期，格式为2025_MM_DD.txt"""
    date_str = chunk_id.replace('.txt', '')
    date_str = date_str.replace('_', '-')
    return datetime.datetime.strptime(date_str, '%Y-%m-%d')

def sort_log_data():
    """对日志数据按日期排序"""
    data_path = "data/json_data/data_json_log.json"
    #data_path = "data/json_data/test_json_log.json"
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    sorted_data = sorted(data, key=lambda x: extract_date_from_chunk_id(x['chunk_id']), reverse=True)
    
    with open(data_path, 'w', encoding='utf-8') as f:
        json.dump(sorted_data, f, ensure_ascii=False, indent=2)
    
    logger.info("数据已按日期从大到小排序完成！")
    logger.info(f"总共处理了 {len(sorted_data)} 条记录")
    if sorted_data:
        logger.info("最新一条日志的日期：")
        date = extract_date_from_chunk_id(sorted_data[0]['chunk_id'])
        logger.info(f"{sorted_data[0]['chunk_id']} - {date.strftime('%Y年%m月%d日')}")
        return date
    else:
        # 如果没有现有数据，返回一个默认的早期日期
        return datetime.datetime(2025, 6, 1)

def get_unadded_log_list():
    """获取未添加的日志列表"""
    last_log_date = sort_log_data()
    today_date = datetime.datetime.today().date()  
    last_log_date = last_log_date.date()  
    
    # 从最后一天的下一天开始
    start_date = last_log_date + datetime.timedelta(days=1)
    # 生成从start_date到今天的日期列表（包含今天）
    unadded_log_list = []
    current_date = start_date
    while current_date <= today_date:  
        unadded_log_list.append(current_date.strftime("%Y_%m_%d.txt"))
        current_date += datetime.timedelta(days=1)
    
    return unadded_log_list



#====================请求文件内容===========================
def fetch_logs(log_filenames: list[str]) -> list[dict]:
    """从API获取日志数据"""
    url = "http://localhost:5000/api/get_files"  # 服务端端口
    try:
        payload = {
            "type": "操作日志",
            "filenames": log_filenames
        }
        response = requests.post(url, json=payload)
        return response.json() 
    except Exception as e:
        logger.error(f"请求日志失败: {e}")
        return []

def download_log(log_list):
    """下载日志文件到本地"""
    log_paths = []
    for log in log_list:
        if log['content'] != '':
            date = log['name']
            content = log['content']
            log_path = f"data/raw_data/japan_shrimp/{date}"
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(content)
            log_paths.append(log_path)
    return log_paths



#====================更新日志json数据和embedding到知识库===========================
def structure_log(log_list):
    """结构化日志数据"""
    logs_data = []
    log_paths = download_log(log_list)
    if log_paths:
        logger.info("已下载最新操作日志源文件：" + str(log_paths))
        for log_path in log_paths:
            logs_data.extend(clean_log_file(log_path)) 
    
    if not logs_data:
        logger.info("没有新的日志数据需要处理")
        return []
    
    data = logs_data[:]
    # 读取现有数据
    try:
        with open('data/json_data/data_json_log.json', 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
            logs_data.extend(existing_data)
    except FileNotFoundError:
        logger.info("创建新的日志数据文件")
    
    # 保存更新后的数据
    with open('data/json_data/data_json_log.json', 'w', encoding='utf-8') as f:
        json.dump(logs_data, f, ensure_ascii=False, indent=2)
    logger.info("已将最新操作日志添加到data_json_log.json文件中")
    return data

def embedding_log(log_list, chunk_type=chunk_data_for_log, max_tokens=500):
    """向量化日志数据"""
    logs_data = structure_log(log_list)
    embedding_for_log = RAG(collection_name="log")
    embedding_for_log.embedding(data=logs_data, chunk_type=chunk_type, max_tokens=max_tokens)
    logger.info("已将最新操作日志向量化到log库中")
    embedding_for_log = RAG(collection_name="all_data")
    embedding_for_log.embedding(data=logs_data, chunk_type=chunk_type, max_tokens=max_tokens)
    logger.info("已将最新操作日志向量化到log库中")
    '''# 向量化到all_data库
    embedding_for_log = RAG(collection_name="all_data")
    embedding_for_log.embedding(data=logs_data, chunk_type=chunk_type, max_tokens=max_tokens)
    logger.info("已将最新操作日志向量化到all_data库中")
    
    # 向量化到log库
    embedding_for_log = RAG(collection_name="log")
    embedding_for_log.embedding(data=logs_data, chunk_type=chunk_type, max_tokens=max_tokens)   
    logger.info("已将最新操作日志向量化到log库中")'''

#====================运行定时日志获取和处理===========================
def run_daily_log_fetch():
    """运行日常日志获取和处理"""
    missing_logs = get_unadded_log_list() 
    if not missing_logs:
        logger.info("已更新到最新版日志")
        return
    log_list = []
    logger.info(f"正在请求日志文件{(missing_logs)}...")
    logs_data = fetch_logs(missing_logs)
    print(logs_data)
    logs_data = logs_data["data"] 

    for filename, content in list(logs_data.items()): 
        if isinstance(content, dict) and "error" in content:
            logger.error(f"获取日志失败: {content['error']}")
            del logs_data[filename]
        else:
            log = {"name": filename, "content": content}
            log_list.append(log)

    # 处理和向量化日志
    embedding_log(log_list, chunk_type=chunk_data_for_log, max_tokens=500) 

def scheduled_task():
    """定时任务"""
    logger.info(f"=== 定时任务执行 - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    run_daily_log_fetch()
    logger.info("=== 任务完成 ===\n")

def run_scheduler(time_str="23:59"):
    """启动定时调度器
    Args:
        time_str: 执行时间（HH:MM格式，默认23:59）
    """
    logger.info(f"启动定时任务，每天 {time_str} 执行一次")
    logger.info("按 Ctrl+C 停止定时任务")
    # 设置定时任务
    schedule.every().day.at(time_str).do(scheduled_task)
    # 启动时立即执行一次
    scheduled_task()
    # 循环执行定时任务
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  
    except KeyboardInterrupt:
        logger.info("\n定时任务已停止")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='日志自动化处理系统')
    parser.add_argument('--schedule', '-s', action='store_true', help='启动定时任务模式')
    parser.add_argument('--time', '-t', type=str, default="23:59", help='定时任务执行时间（HH:MM格式，默认23:59）')
    parser.add_argument('--manual', '-m', action='store_true', help='手动执行一次日志处理')
    
    args = parser.parse_args()
    
    if args.schedule:
        run_scheduler(args.time)
    elif args.manual:
        run_daily_log_fetch()
    else:
        # 默认显示未添加的日志列表
        unadded_log_list = get_unadded_log_list()
        logger.info(f"未添加的日志列表: {unadded_log_list}")