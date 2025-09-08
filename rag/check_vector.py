from qdrant_client import QdrantClient

# 连接 Qdrant
client = QdrantClient(path="data/vector_data")

from qdrant_client.http import models as rest

"""
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
        if payload["metadata"]["source"] == "循环水南美白对虾养殖系统设计及操作手册张驰v3.0":
            payload["metadata"]["source"] = "data/raw_data/japan_shrimp/循环水南美白对虾养殖系统设计及操作手册张驰v3.0.pdf"
        if payload["metadata"]["source"] == "饲料手册":
            payload["metadata"]["source"] = "data/raw_data/japan_shrimp/喂食器参数与设置.txt"
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

print("所有点的字段已改` ✅")"""

# 1. 查看有哪些 collections
print("=== Collections 列表 ===")
print(client.get_collections())

# 2. 指定要对比的 collection 名称
camel_collection = "japan_shrimp"
# 3. 查看 collection 配置 (vector size / distance 等)
print("\n=== ALL Collection Info ===")
print(client.get_collection(camel_collection))

# 4. 查看前几条数据（包含向量）
print("\n=== CAMEL 数据样例 ===")
camel_points, next_page = client.scroll(
    collection_name=camel_collection,
    limit=10,
    with_payload=True,   # 默认 True，可以省略
    with_vectors=True    # 关键参数：把向量也取出来
)

for p in camel_points:
    print("ID:", p.id)
    print("Payload:", p.payload)
    if isinstance(p.vector, dict):
        # 如果 collection 有多个向量命名空间，vector 是 dict
        vec = list(p.vector.values())[0]
    else:
        vec = p.vector
    print("Vector 维度:", len(vec))
    print("Vector (前50维):", vec[:50], "...")
    print("-" * 60)
