from qdrant_client import QdrantClient

# 连接 Qdrant
client = QdrantClient(path="data/vector_data")

from qdrant_client.http import models as rest


collection_name = "japan_shrimp"

# 分批 scroll 读取所有点
scroll_cursor = None

while True:
    points, scroll_cursor = client.scroll(
        collection_name=collection_name,
        limit=100,  # 每次批量 100 个，可以调大/调小
        offset=scroll_cursor,
        with_vectors=True  # 保证 vector 一起读出，方便回写
    )

    if not points:
        break

    new_points = []

    for p in points:
        payload = p.payload.copy()
        if "text" in payload:
            payload["page_content"] = payload.pop("text")  # 改字段名
        if payload["extra_info"]["type"] == "text":
            payload["metadata"]["source"] = "循环水南美白对虾养殖系统设计及操作手册张驰v3.0"  # 改字段名
        elif payload["extra_info"]["type"] == "table":
            payload["metadata"]["source"] = "循环水南美白对虾养殖系统设计及操作手册张驰v3.0"  # 改字段名
        elif payload["extra_info"]["type"] == "log":
            payload["metadata"]["source"] = "操作日志"  # 改字段名
        elif payload["extra_info"]["type"] == "feed":
            payload["metadata"]["source"] = "饲料手册"  # 改字段名
        new_points.append(
            rest.PointStruct(
                id=p.id,
                vector=p.vector,     # 保持原始向量
                payload=payload      # 更新后的 payload
            )
        )

    # 回写更新
    client.upsert(
        collection_name=collection_name,
        points=new_points
    )
    
    # 如果没有更多数据了，退出循环
    if not scroll_cursor:
        break

print("所有点的字段已改` ✅")



# 1. 查看有哪些 collections
print("=== Collections 列表 ===")
print(client.get_collections())

# 2. 指定要对比的 collection 名称
camel_collection = "japan_shrimp"
langchain_collection = "bank"
# 3. 查看 collection 配置 (vector size / distance 等)
print("\n=== ALL Collection Info ===")
print(client.get_collection(camel_collection))
print("\n=== LangChain Collection Info ===")
print(client.get_collection(langchain_collection))

# 4. 查看每个 collection 的前几条数据
print("\n=== CAMEL 数据样例 ===")
camel_points = client.scroll(collection_name=camel_collection, limit=3)[0]
for p in camel_points:
    print(p.payload)



print("\n=== LangChain 数据样例 ===")
langchain_points = client.scroll(collection_name=langchain_collection, limit=3)[0]
for p in langchain_points:
    print(p.payload)


