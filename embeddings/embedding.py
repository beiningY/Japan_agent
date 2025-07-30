import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from embeddings.vr_chunking import chunk_data_for_log, chunk_data_by_title
from rag import RAG

embedding_for_all_data = RAG(collection_name="all_data")
embedding_for_all_data.embedding(data_path="data/cleand_data/data_json_book_zh.json", chunk_type=chunk_data_by_title, max_tokens=500)
embedding_for_all_data.embedding(data_path="data/cleand_data/data_json_feed.json", chunk_type=chunk_data_by_title, max_tokens=500)
embedding_for_all_data.embedding(data_path="data/cleand_data/data_json_log.json", chunk_type=chunk_data_for_log, max_tokens=500)

embedding_for_book_zh = RAG(collection_name="book_zh")

embedding_for_book_zh.embedding(data_path="data/cleand_data/data_json_book_zh.json", chunk_type=chunk_data_by_title, max_tokens=500)

embedding_for_book_zh.embedding(data_path="data/cleand_data/data_json_feed.json", chunk_type=chunk_data_by_title, max_tokens=500)

embedding_for_log = RAG(collection_name="log")
embedding_for_log.embedding(data_path="data/cleand_data/data_json_log.json", chunk_type=chunk_data_for_log, max_tokens=500)


