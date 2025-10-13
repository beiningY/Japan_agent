"""
联网搜索工具模块
使用 Tavily API 进行联网搜索
"""
import logging
import os
from typing import List, Dict, Any
from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# 从环境变量获取 API Key，提高安全性
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "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")


def web_search(query: str, max_results: int = 3, search_depth: str = "basic") -> List[Dict[str, Any]]:
    """
    通过 Tavily API 进行联网搜索
    
    Args:
        query: 搜索查询字符串
        max_results: 返回的最大结果数量，默认为3
        search_depth: 搜索深度，可选值: "basic" 或 "advanced"，默认为 "basic"
    
    Returns:
        包含搜索结果的列表，每个结果包含 title, url, content, score 等字段
    """
    try:
        logger.info(f"执行联网搜索，查询: {query}, 最大结果数: {max_results}")
        
        tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
        
        # 调用 Tavily API
        response = tavily_client.search(
            query=query,
            max_results=max_results,
            search_depth=search_depth,
            include_answer=True
        )
        
        results = response.get("results", [])
        answer = response.get("answer", "")
        
        # 过滤和格式化结果
        formatted_results = []
        for result in results:
            # 只返回相关性分数大于 0.5 的结果
            if result.get("score", 0) > 0.5:
                formatted_results.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "content": result.get("content", ""),
                    "score": result.get("score", 0),
                    "published_date": result.get("published_date", "")
                })
        
        logger.info(f"搜索完成，返回 {len(formatted_results)} 条结果")
        
        # 如果有答案，添加到结果的第一项
        if answer:
            return {
                "answer": answer,
                "results": formatted_results,
                "total_results": len(formatted_results)
            }
        
        return {
            "results": formatted_results,
            "total_results": len(formatted_results)
        }
        
    except Exception as e:
        logger.error(f"联网搜索失败: {str(e)}")
        return {
            "error": str(e),
            "results": [],
            "total_results": 0
        }


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    # 测试联网搜索
    result = web_search("Python programming best practices", max_results=3)
    print("联网搜索结果:")
    print(result)
