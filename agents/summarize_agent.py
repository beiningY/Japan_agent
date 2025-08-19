from .camel_single_agent import CamelSingleAgent
import logging

logger = logging.getLogger("SummarizeAgent")
logger.setLevel(logging.INFO)

class SummarizeAgent:
    def summarize(self, query: str, answer: str, chat_result: str) : 
        summarize_agent = CamelSingleAgent(
            rag = False ,
            temperature=0.4,
            system_message = (
                f"你是一个擅长总结并回答问题的专家，你的任务是根据用户的问题参考单智能体和场景对话两种不同的答案，总结并给出最终的最准确的答案。"
            ),
            max_tokens=4096
        )
        input = f"""用户的问题是：{query}
单智能体的回答是：{answer}
养殖员和专家顾问讨论的对话是：{chat_result}
请你参考单智能体和讨论对话两种不同的回答。你需要根据用户的问题总结并给出最终最准确的答案
切记你是一个对于陆上循环水养殖南美白对虾系统的专家。问题的答案请围绕这个主题展开回答，一定要抓取对话中的对答案有帮助的真实检索到的信息，一定要确保数据准确有源头。如果场景对话的内容偏离用户问题主题就忽略，参考单智能体的回答。
"""
        result = summarize_agent.run(input)
        result = result.strip()
        logger.info(f"总结结果:{result}")
        return result
    
    def stream(self, query: str, answer: str, chat_result: str):
        result = self.summarize(query, answer, chat_result)
        yield {
            "agent_type": "summarize_agent",
            "agent_response": result
        }

