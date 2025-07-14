import os
from datetime import datetime
from pathlib import Path
import json
def clean_text(log):
    clean_text = log.replace('\n', '') 
    clean_text = clean_text.replace(' ', '')
    return clean_text

def clean_log_file(file_path):
    path = Path(file_path)
    filename = path.name
    with open(file_path, "r", encoding="utf-8") as f:
        title = f.readline().strip()
        log = f.read().strip()
        clean_text = clean_text(log)
        chunk = {
            "chunk_id": filename,
            "chapter": "操作日志",
            "title1": title,
            "content": clean_text,
            "type": "log"
        }
    return chunk  

def get_today_log_file(log_dir):
    today_str = datetime.ay().strftime("%Y_%m_%d.txt")
    return os.path.join(log_dir, today_str)

def clean_today_log(log_dir):
    file_path = get_today_log_file(log_dir)
    return clean_log_file(file_path)

def process_today_logs():
    log_dir = "../data/raw_data/log"
    file_path = get_today_log_file(log_dir)
    if not file_path:
        print("没有找到今天的日志文件")
        return
    chunk = clean_today_log(file_path)
    print(f"处理{chunk}日志")


def  get_unadded_log_list():
    added_log_path = "../data/cleand_data/data_json_log.json"
    with open(added_log_path, "r", encoding="utf-8") as f:
        added_log_list = json.load(f)
    return added_log_list