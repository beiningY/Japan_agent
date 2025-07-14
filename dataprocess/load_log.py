import json
import copy
from dataprocess.clean_log import clean_log_file
from dataprocess.get_unadded_data import get_unadded_log_list
from retrievers import RAG
from embeddings.vr_chunking import chunk_data_for_log, chunk_data_by_title

def download_log(log_list):
    log_paths = []
    for log in log_list:
        if log['content'] != '':
            date = log['name']
            content = log['content']
            log_path = f"data/raw_data/log/{date}.txt"
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(content)
            log_paths.append(log_path)
    return log_paths

def structure_log(log_paths):
    logs_data = []
    #log_paths = download_log(log_list)
    for log_path in log_paths:
        logs_data.extend(clean_log_file(log_path)) 
    data = logs_data[:]
    print(data)
    with open('data/cleand_data/data_json_log.json', 'r', encoding='utf-8') as f:
        existing_data = json.load(f)
        logs_data.extend(existing_data) 
    with open('data/cleand_data/data_json_log.json', 'w', encoding='utf-8') as f:
        json.dump(logs_data, f, ensure_ascii=False, indent=2)
    print(data)
    return data

def embedding_log(log_list,chunk_type=chunk_data_for_log,max_tokens=500):
    logs_data = structure_log(log_list)
    embedding_for_log = RAG(collection_name="all_data")
    embedding_for_log.embedding(data=logs_data, chunk_type=chunk_type, max_tokens=max_tokens)
    embedding_for_log = RAG(collection_name="log")
    embedding_for_log.embedding(data=logs_data, chunk_type=chunk_type, max_tokens=max_tokens)   

if __name__ == "__main__":
    log_paths = ["data/raw_data/log/2025_07_03.txt", "data/raw_data/log/2025_07_04.txt", "data/raw_data/log/2025_07_07.txt", "data/raw_data/log/2025_07_08.txt", "data/raw_data/log/2025_07_09.txt"]

    embedding_log(log_paths,chunk_type=chunk_data_for_log,max_tokens=500)