#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查Qdrant向量数据库中的向量数据状态
"""

import json
import os
from camel.storages import QdrantStorage
from camel.embeddings import SentenceTransformerEncoder
from camel.retrievers import VectorRetriever

def check_qdrant_collections():
    """检查Qdrant中的所有集合"""
    print("=" * 50)
    print("检查Qdrant向量数据库状态")
    print("=" * 50)
    
    # 检查不同的存储路径
    storage_paths = [
        "data/vector_data"
    ]
    # 尝试加载embedding模型来获取向量维度
    embedding_model = SentenceTransformerEncoder(model_name="models/multilingual-e5-large")
    vector_dim = embedding_model.get_output_dim()
    for storage_path in storage_paths:
        if os.path.exists(storage_path):
            print(f"\n 检查存储路径: {storage_path}")
            try:
                # 检查该路径下的所有集合
                if os.path.exists(os.path.join(storage_path, "meta.json")):
                    with open(os.path.join(storage_path, "meta.json"), "r") as f:
                        meta_data = json.load(f)
                    
                    collections = meta_data.get("collections", {})
                    if collections:
                        print(f"  发现 {len(collections)} 个集合:")
                        for collection_name, collection_info in collections.items():
                            print(f"     集合名称: {collection_name}")
                            
                            # 获取向量配置信息
                            vectors_config = collection_info.get("vectors", {})
                            vector_size = vectors_config.get("size", "未知")
                            distance = vectors_config.get("distance", "未知")
                            
                            print(f"      向量维度: {vector_size}")
                            print(f"      距离度量: {distance}")
                            
                            # 尝试连接到集合并获取向量数量
                            try:
                                storage = QdrantStorage(
                                    vector_dim=vector_dim,
                                    path=storage_path,
                                    collection_name=collection_name
                                )
                                
                                # 获取集合信息
                                collection_info = storage.client.get_collection(collection_name)
                                vector_count = collection_info.points_count
                                print(f"      向量数量: {vector_count}")
                                
                                # 如果向量数量大于0，显示一些示例
                                if vector_count > 0:
                                    print(f"       集合包含向量数据")
                                    
                                    # 获取一些示例向量
                                    try:
                                        points = storage.client.scroll(
                                            collection_name=collection_name,
                                            limit=20,
                                            with_payload=True,
                                            with_vectors=False
                                        )[0]
                                        
                                        if points:
                                            print(f"      示例数据:")
                                            for i, point in enumerate(points):
                                                payload = point.payload
                                                print(f"        示例 {i+1}: {payload.get('text', '无文本')[:100]}...")
                                                print(payload)
                                    except Exception as e:
                                        print(f"      无法获取示例数据: {e}")
                                else:
                                    print(f"      ❌ 集合为空")
                                    
                            except Exception as e:
                                print(f"      无法连接到集合: {e}")
                            
                            print()
                    else:
                        print("   ❌ 未发现任何集合")
                else:
                    print("   ❌ 未找到meta.json文件")
                    
            except Exception as e:
                print(f"   ❌ 检查失败: {e}")
        else:
            print(f"\n 存储路径不存在: {storage_path}")

def check_specific_collection(collection_name, storage_path="data/knowledge_base"):
    """检查特定集合的详细信息"""
    print(f"\n详细检查集合: {collection_name}")
    print("=" * 50)
    
    try:
        # 加载embedding模型
        embedding_model = SentenceTransformerEncoder(model_name="models/multilingual-e5-large")
        vector_dim = embedding_model.get_output_dim()
        
        # 创建存储连接
        storage = QdrantStorage(
            vector_dim=vector_dim,
            path=storage_path,
            collection_name=collection_name
        )
        
        # 获取集合信息
        collection_info = storage.client.get_collection(collection_name)
        vector_count = collection_info.points_count
        
        print(f"集合名称: {collection_name}")
        print(f"向量数量: {vector_count}")
        print(f"向量维度: {vector_dim}")
        
        if vector_count > 0:
            # 获取一些示例数据
            points = storage.client.scroll(
                collection_name=collection_name,
                limit=5,
                with_payload=True,
                with_vectors=False
            )[0]
            
            print(f"\n前5个向量数据示例:")
            for i, point in enumerate(points):
                payload = point.payload
                print(f"\n示例 {i+1}:")
                print(f"  ID: {point.id}")
                print(f"  文本: {payload.get('text', '无文本')[:200]}...")
                print(f"  额外信息: {payload.get('extra_info', '无')}")
                
        else:
            print(" 集合为空，没有向量数据")
            
    except Exception as e:
        print(f" 检查失败: {e}")

def main():
    """主函数"""
    # 检查所有集合
    check_qdrant_collections()

if __name__ == "__main__":
    main() 