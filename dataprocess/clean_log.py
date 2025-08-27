from pathlib import Path
import json
from embeddings.japan_book_chunking import chunk_data_for_log
from rag.camel_rag import CamelRAG

def clean_log(log):
    clean_text = log.replace('\n', '') 
    clean_text = clean_text.replace(' ', '')
    return clean_text

def clean_log_file(file_path):
    path = Path(file_path)
    filename = path.name
    chunks = []
    with open(file_path, "r", encoding="utf-8") as f:
        title = f.readline().strip()
        log = f.read().strip()
        clean_text = clean_log(log)
        chunk = {
            "chunk_id": filename,
            "chapter": "操作日志",
            "title1": title,
            "content": clean_text,
            "type": "log"
        }
        chunks.append(chunk)
    return chunks   

if __name__ == "__main__":
    json_file = "data/cleand_data/data_json_log.json"
    log_file = "data/raw_data/log/2025_07_14.txt"
    chunk = clean_log_file(log_file)
    with open(json_file, 'r', encoding='utf-8') as f:
        existing_data = json.load(f)
        existing_data.extend(chunk)
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, ensure_ascii=False, indent=2)
    print(f"\n共提取 {len(chunk)} 个有效内容块，已保存至 {json_file}")
    embedding_for_all_data = RAG(collection_name="all_data")
    embedding_for_all_data.embedding(data=chunk, chunk_type=chunk_data_for_log, max_tokens=500)
    embedding_for_log = RAG(collection_name="log")
    embedding_for_log.embedding(data=chunk, chunk_type=chunk_data_for_log, max_tokens=500)