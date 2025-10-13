"""
测试联网搜索工具
"""
import sys
import os
import asyncio
import logging

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ToolOrchestrator.tools import web_search_tools

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_web_search():
    """测试基本联网搜索功能"""
    logger.info("=" * 50)
    logger.info("测试基本联网搜索功能")
    logger.info("=" * 50)
    
    query = "Python 最新版本特性"
    result = web_search_tools.web_search(query, max_results=3, search_depth="basic")
    
    logger.info(f"\n查询: {query}")
    logger.info(f"结果数量: {result.get('total_results', 0)}")
    
    if "answer" in result:
        logger.info(f"\n摘要答案:\n{result['answer']}\n")
    
    if result.get('results'):
        logger.info("\n搜索结果:")
        for i, item in enumerate(result['results'], 1):
            logger.info(f"\n{i}. {item.get('title', 'N/A')}")
            logger.info(f"   URL: {item.get('url', 'N/A')}")
            logger.info(f"   相关性分数: {item.get('score', 0):.3f}")
            logger.info(f"   内容摘要: {item.get('content', 'N/A')[:100]}...")
    
    if "error" in result:
        logger.error(f"搜索出错: {result['error']}")
        return False
    
    return True


def test_advanced_search():
    """测试高级搜索功能"""
    logger.info("\n" + "=" * 50)
    logger.info("测试高级搜索功能")
    logger.info("=" * 50)
    
    query = "大语言模型的应用场景"
    result = web_search_tools.web_search(query, max_results=5, search_depth="advanced")
    
    logger.info(f"\n查询: {query} (高级搜索)")
    logger.info(f"结果数量: {result.get('total_results', 0)}")
    
    if "answer" in result:
        logger.info(f"\n摘要答案:\n{result['answer']}\n")
    
    if result.get('results'):
        logger.info(f"\n找到 {len(result['results'])} 条相关结果")
        for i, item in enumerate(result['results'][:3], 1):  # 只显示前3条
            logger.info(f"\n{i}. {item.get('title', 'N/A')}")
            logger.info(f"   相关性分数: {item.get('score', 0):.3f}")
    
    if "error" in result:
        logger.error(f"搜索出错: {result['error']}")
        return False
    
    return True


async def test_client_integration():
    """测试通过 MCP Client 调用工具"""
    logger.info("\n" + "=" * 50)
    logger.info("测试通过 MCP Client 调用工具")
    logger.info("=" * 50)
    
    try:
        from ToolOrchestrator.client.client import MultiServerMCPClient
        
        # 创建客户端
        client = MultiServerMCPClient(config={})
        
        # 获取工具列表
        tools = await client.get_tools()
        logger.info(f"\n可用工具数量: {len(tools)}")
        
        # 查找 web_search 工具
        web_search_found = any(t.name == "web_search" for t in tools)
        
        logger.info(f"web_search 工具是否可用: {web_search_found}")
        
        if web_search_found:
            # 测试调用 web_search
            result = await client.invoke("web_search", {
                "query": "今天天气怎么样",
                "max_results": 2
            })
            logger.info(f"\n通过 Client 调用 web_search:")
            logger.info(f"状态: {result.get('status')}")
            if result.get('status') == 'ok':
                logger.info(f"结果数量: {result.get('result', {}).get('total_results', 0)}")
        
        await client.close()
        return web_search_found
        
    except Exception as e:
        logger.error(f"Client 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    logger.info("\n开始运行联网搜索工具测试套件\n")
    
    results = {
        "基本搜索测试": False,
        "高级搜索测试": False,
        "Client 集成测试": False
    }
    
    # 测试1: 基本搜索
    try:
        results["基本搜索测试"] = test_web_search()
    except Exception as e:
        logger.error(f"基本搜索测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试2: 高级搜索
    try:
        results["高级搜索测试"] = test_advanced_search()
    except Exception as e:
        logger.error(f"高级搜索测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试3: Client 集成
    try:
        results["Client 集成测试"] = asyncio.run(test_client_integration())
    except Exception as e:
        logger.error(f"Client 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 输出测试总结
    logger.info("\n" + "=" * 50)
    logger.info("测试结果总结")
    logger.info("=" * 50)
    
    for test_name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        logger.info(f"{test_name}: {status}")
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    logger.info(f"\n总计: {passed_tests}/{total_tests} 个测试通过")
    
    if passed_tests == total_tests:
        logger.info("\n🎉 所有测试通过！")
        return 0
    else:
        logger.warning(f"\n⚠️  {total_tests - passed_tests} 个测试失败")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

