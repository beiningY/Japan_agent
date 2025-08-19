from agents import CamelSingleAgent, CamelRoleplayAgent, JudgeAgent, SummarizeAgent
import logging

logger = logging.getLogger("MultiAgent")
logger.setLevel(logging.INFO)
class MultiAgent:
    def simple_agent(self, query: str):
        """单智能体"""
        try:
            # 创建单智能体
            logger.info(f"单智能体启动，处理查询: {query}")
            single_agent = CamelSingleAgent()
            result = single_agent.run(query)
            logger.info("单智能体处理完成")
            return result
        except Exception as e:
            logger.error(f"单智能体处理失败: {str(e)}")
            return {"error": str(e), "agent_response": "单智能体处理过程中出现错误"}

    def roleplay_agent(self, query: str):
        """判断是否需要启用多智能体写作场景"""
        try:
            # 创建场景对话智能体
            logger.info(f"场景对话智能体启动，处理查询: {query}")
            roleplay_agent = CamelRoleplayAgent(max_tokens=10000)
            result = roleplay_agent.run(query)
            logger.info("场景对话智能体处理完成")
            return result
        except Exception as e:
            logger.error(f"场景对话智能体处理失败: {str(e)}")
            return {"error": str(e), "agent_response": "场景对话智能体处理过程中出现错误"}

    def run(self, query: str):
        """主函数，协调单智能体和判断智能体"""
        try:
            answer1 = self.simple_agent(query)
            judge_result = JudgeAgent().judge(query, answer1)
            if judge_result == "YES":
                logger.info("判断结果：单智能体回答已满足问题需求")
                return answer1
            elif judge_result == "NO":
                logger.info(f"判断结果:{judge_result}，问题被归类为复杂问题，将启用多轮场景对话模式进行辅助分析。")
                answer2 = self.roleplay_agent(query)
                summarize_result = SummarizeAgent().summarize(query, answer1, answer2)
                return answer1, answer2, summarize_result
            else:
                logger.info(f"判断结果:{judge_result}，回答不符合格式，返回单智能体答案。")
                return answer1
        except Exception as e:
            logger.error(f"主函数处理失败: {str(e)}")
            return {"error": str(e), "agent_response": "多智能体处理过程中出现错误"}

        