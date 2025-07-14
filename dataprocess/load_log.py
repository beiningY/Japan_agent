import json
from dataprocess.clean_log import clean_log_file
from dataprocess.get_unadded_data import get_unadded_log_list
from retrievers import RAG
from embeddings.vr_chunking import chunk_data_for_log, chunk_data_by_title

def download_log(log_list):
    log_paths = []
    for log in log_list:
        date = log['name']
        content = log['content']
        log_path = f"data/raw_data/log/{date}.txt"
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(content)
        log_paths.append(log_path)
    return log_paths

def structure_log(log_list):
    logs_data = []
    log_paths = download_log(log_list)
    for log_path in log_paths:
        logs_data.extend(clean_log_file(log_path))
    with open('data/cleand_data/data_json_log.json', 'w', encoding='utf-8') as f:
        json.dump(logs_data, f, ensure_ascii=False, indent=2)
    return logs_data

def embedding_log(log_list,collection_name="all_data",chunk_type=chunk_data_for_log,max_tokens=500):
    logs_data = structure_log(log_list)
    embedding_for_log = RAG(collection_name=collection_name)
    embedding_for_log.embedding(data=logs_data, chunk_type=chunk_type, max_tokens=max_tokens)

if __name__ == "__main__":
    log_list = get_unadded_log_list()
    embedding_log(log_list)
    log_list = [
        {'name': '2025_07_08.txt', 'content': '7月3日星期四，晴，气温24～32摄氏度。'},
        {'name': '2025_07_09.txt', 'content': '一号池。水温27.6摄氏度，pH 9.02，氨氮0，亚硝酸盐 0。循环运行。清理物理过滤器。'},
        {'name': '2025_07_10.txt', 'content': '二号池运转正常。水温28.4摄氏度，pH 9.12，氨氮0，亚硝酸盐 0。浓缩污水上清液返流系统工作正常，并清洗污水桶。清洗物理过滤器。'},
        {'name': '2025_07_11.txt', 'content': '每日关键点总结：1.2号池喂食盘未有剩余，明日继续观察。白虾大部分已经度过转肝期，即将进入快速成长阶段。'},
        {'name': '2025_07_12.txt', 'content': '检查所有运转中设备，不漏水.不断气.没有断电风险。'}
    ]
    embedding_log(log_list,collection_name="test",chunk_type=chunk_data_for_log,max_tokens=500)