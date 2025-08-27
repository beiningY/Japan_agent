import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from embeddings.japan_book_chunking import chunk_data_for_log, chunk_data_by_title
from rag.camel_rag import CamelRAG

embedding_for_all_data = CamelRAG(collection_name="japan_shrimp")
embedding_for_all_data.embedding(data_path="data/json_data/data_json_book_zh.json", chunk_type=chunk_data_by_title, max_tokens=500)
#embedding_for_all_data.embedding(data_path="data/json_data/data_json_feed.json", chunk_type=chunk_data_by_title, max_tokens=500)
#embedding_for_all_data.embedding(data_path="data/json_data/data_json_log.json", chunk_type=chunk_data_for_log, max_tokens=500)