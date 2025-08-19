from qdrant_client import QdrantClient

# 连接 Qdrant
client = QdrantClient(path="data/vector_data")

# 1. 查看有哪些 collections
print("=== Collections 列表 ===")
print(client.get_collections())

# 2. 指定要对比的 collection 名称
camel_collection = "all_data"
langchain_collection = "bank"

# 3. 查看 collection 配置 (vector size / distance 等)
print("\n=== CAMEL Collection Info ===")
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
