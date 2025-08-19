from .camel_single_agent import CamelSingleAgent
import logging

logger = logging.getLogger("JudgeAgent")
logger.setLevel(logging.INFO)

class JudgeAgent:
    def judge(self, query: str, answer: str) : 
        judge_agent = CamelSingleAgent(
            rag = False,
            temperature=0.4,
            system_message = (
                f"如果需要再进行深度讨论和进一步检索等方法请回复：'NO'。如果答案已经非常详细并且全面准确解决了问题，请回复：'YES'.如果回答'YES'首先需要确保用户的问题非常非常简单并且回答的过程不需要推理不需要思考。否则请回答'NO'。请只回答YES或NO，不要解释。"
            ),
            max_tokens=4096
        )
        input = f"用户的问题是：{query}\n回答是：{answer}"
        result = judge_agent.run(input)
        result = result.strip().upper()
        logger.info(f"judge_agent已完成判断。")
        return result
