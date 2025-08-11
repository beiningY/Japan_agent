
from agents import AgentWithRAG, JudgeAgent
import logging
import traceback
from typing import Dict, Any, Generator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("JapanQA")
logger.setLevel(logging.INFO)


def simple_agent(query: str) -> Generator[Dict[str, Any], None, Dict[str, Any]]:
    """单智能体"""
    try:
        # 创建单智能体
        logger.info(f"单智能体启动，处理查询: {query}")
        chat_agent = AgentWithRAG()
        result = yield from chat_agent.run(query)
        logger.info("单智能体处理完成")
        return result
    except Exception as e:
        logger.error(f"单智能体处理失败: {str(e)}")
        logger.error(traceback.format_exc())
        return {"error": str(e), "agent_response": "处理过程中出现错误"}

def multi_agent(query: str, answer: str) -> Generator[Dict[str, Any], None, Dict[str, Any]]:
    """判断是否需要启用多智能体写作场景"""
    try:
        logger.info(f"判断是否需要启用多智能体协作场景...")
        judge_agent = JudgeAgent()
        result = yield from judge_agent.judge(query, answer)
        logger.info("判断完成")
        return result
    except Exception as e:
        logger.error(f"判断过程失败: {str(e)}")
        logger.error(traceback.format_exc())
        return {"error": str(e), "judgment": "判断过程中出现错误"}

def main(query: str) -> Generator[Dict[str, Any], None, Dict[str, Any]]:
    """主函数，协调单智能体和判断智能体"""
    try:
        logger.info(f"开始处理查询: {query}")

        answer1 = yield from simple_agent(query)
        
        # 检查单智能体是否成功
        if "error" in answer1:
            logger.error("单智能体处理失败，停止后续处理")
            return
            
        answer2 = yield from multi_agent(query, answer1)
        
    except Exception as e:
        logger.error(f"主函数处理失败: {str(e)}")
        logger.error(traceback.format_exc())
        yield {"error": str(e), "agent_response": "处理过程中出现错误"}
        

if __name__ == "__main__":
    query = "请根据操作日志里的内容告诉我7月20号喂食量有多少"
    logger.info("开始执行测试查询")
    
    try:
        # 创建生成器并运行
        gen = main(query)
        for result in gen:
            print(f"结果: {result}")
    except Exception as e:
        logger.error(f"测试执行失败: {str(e)}")
        logger.error(traceback.format_exc())
    