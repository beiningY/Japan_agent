# agents/single_agent.py
"""
极简Agent - 固定执行两个工具，零中间层，最快速度
执行流程：
1. 使用小模型（gpt-4o-mini）快速生成SQL查询
2. 固定执行 retrieve 知识库检索
3. 固定执行 read_query_for_sensor_readings 传感器数据查询（使用生成的SQL）
4. 将所有结果拼接到prompt中，一次生成最终答案
"""
from __future__ import annotations
import os
import json
import asyncio
from typing import List, Dict, Any, Optional, Generator
from openai import OpenAI
from ToolOrchestrator.client.client import MultiServerMCPClient
from ToolOrchestrator.core.config import settings
from utils.logger import get_logger
from dotenv import load_dotenv
load_dotenv()
logger = get_logger(__name__)


class SingleAgent:
    """
    极简Agent实现 - 固定执行两个工具后生成答案
    - 不使用OpenAI tools功能，不需要模型决策
    - 固定执行retrieve和read_query_for_sensor_readings
    - 将结果拼接到prompt中，一次性生成最终答案
    - 完全绕过ToolRegistry安全检查层，达到最快响应速度
    """
    
    def __init__(
        self,
        system_prompt: Optional[str] = None,
        model: str = "gpt-4o",
        max_steps: int = 3
    ):
        """
        初始化Agent
        
        Args:
            system_prompt: 系统提示词
            model: OpenAI模型名称
            max_steps: 最大执行步数
        """
        # OpenAI客户端
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("GPT_API_KEY")
        if not api_key:
            raise ValueError("未找到 OPENAI_API_KEY 或 GPT_API_KEY 环境变量")
        self.client = OpenAI(api_key=api_key)
        
        # 配置
        self.model = model
        self.max_steps = max_steps
        
        # 设置默认或自定义系统提示词
        default_prompt = """你可以通过工具查询循环水南美白对虾养殖系统设计及操作手册张驰和ESG综合工程管理文档的内容，也可以通过工具查询sensor_readings表获取传感器数据。请基于工具返回的真实数据回答用户问题，并明确引用来源。
"""
        
        self.system_prompt = system_prompt + default_prompt if system_prompt else default_prompt
        
        # MCP客户端（直接调用，无安全检查）
        self.mcp_client: Optional[MultiServerMCPClient] = None
        
        logger.info(f"SingleAgent 初始化完成，模型: {model}, 最大步数: {max_steps}")
    
    async def initialize(self):
        """异步初始化MCP客户端"""
        if self.mcp_client is not None:
            return
        
        # 直接初始化MCP客户端
        self.mcp_client = MultiServerMCPClient(settings.MCP_CLIENT_CONFIG)
        await self.mcp_client.get_tools()
        
        logger.info("MCP客户端初始化完成，已准备直接调用工具")
    
    async def _generate_sql(self, user_query: str) -> str:
        """
        使用小模型快速生成SQL查询语句
        
        Args:
            user_query: 用户查询
            
        Returns:
            SQL查询语句
        """
        sql_prompt = f"""你是一个SQL生成专家。请根据用户问题生成一个查询sensor_readings表的SQL语句。

sensor_readings表结构：
- id: 主键
- sensor_id: 传感器id
- value: 读数值
- recorded_at: 记录时间
- type_name: 传感器英文类型（dissolved_oxygen_aturation、liquid_level、PH、temperature和turbidity）
- description : 传感器中文描述(溶解氧饱和度、液位、PH、温度和浊度)
- unit: 单位



用户问题：{user_query}

要求：
1. 只返回SQL语句，不要任何解释
2. 如果问题与传感器无关，返回：SELECT * FROM sensor_readings ORDER BY recorded_at DESC LIMIT 10
3. 使用标准SQL语法
4. 限制返回结果不超过100条

SQL语句："""

        try:
            response = self.client.chat.completions.create(
                model="gpt-5", 
                messages=[{"role": "user", "content": sql_prompt}],
                max_completion_tokens=5000
            )
            
            sql_query = response.choices[0].message.content.strip()
            # 清理可能的markdown代码块标记
            sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
            
            logger.info(f"生成的SQL: {sql_query}")
            return sql_query
            
        except Exception as e:
            logger.error(f"SQL生成失败: {e}，使用默认查询")
            return "SELECT * FROM sensor_readings ORDER BY recorded_at DESC LIMIT 10"
    
    def run(self, user_query: str, collection_name: str = "japan_shrimp", k: int = 5) -> Generator[Dict[str, Any], None, None]:
        """
        执行查询任务（同步生成器）- 固定执行两个工具，然后拼接结果生成答案，流式返回。
        """
        import time
        start_time = time.time()

        async def _prepare() -> Dict[str, Any]:
            # 确保工具已初始化
            await self.initialize()

            logger.info(f"开始处理查询: {user_query}")

            # 步骤1&2: 并行执行SQL生成和知识库检索
            logger.info("=== 步骤1&2: 并行执行SQL生成和知识库检索 ===")
            sql_query, retrieve_result = await asyncio.gather(
                self._generate_sql(user_query),
                self.mcp_client.invoke("retrieve", {
                    "collection_name": collection_name,
                    "question": user_query,
                    "k": k
                })
            )
            logger.info(f"SQL生成完成: {sql_query}")
            logger.info("知识库检索完成")

            # 步骤3: 执行传感器数据查询
            logger.info("=== 步骤3: 传感器数据查询 ===")
            sensor_result = await self.mcp_client.invoke("read_query_for_sensor_readings", {
                "table_queries": [
                    {
                        "query": sql_query
                    }
                ]
            })
            logger.info("传感器数据查询完成")

            # 构造包含数据的增强prompt
            enhanced_prompt = f"""请基于以下数据回答用户问题。

【用户问题】
{user_query}

【知识库检索结果】
{json.dumps(retrieve_result, ensure_ascii=False, indent=2)}

【传感器数据查询】
查询结果: {json.dumps(sensor_result, ensure_ascii=False, indent=2)}

请综合以上数据，给出简洁准确的回答。如果无关则忽略数据信息，直接回答用户问题。"""

            return {
                "enhanced_prompt": enhanced_prompt
            }

        # 运行准备阶段（一次事件循环）
        try:
            prep = asyncio.run(_prepare())
        except Exception as e:
            logger.error(f"准备阶段失败: {e}")
            yield {
                "type": "error",
                "content": f"准备阶段失败: {e}"
            }
            return

        enhanced_prompt = prep["enhanced_prompt"]

        # 计算输入token数量（粗略估计）
        def estimate_tokens(text: str) -> int:
            chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
            other_chars = len(text) - chinese_chars
            return int(chinese_chars / 2 + other_chars / 4)

        system_tokens = estimate_tokens(self.system_prompt)
        user_tokens = estimate_tokens(enhanced_prompt)
        total_input_tokens = system_tokens + user_tokens
        logger.info(f"最终答案生成 - 输入token估计: system={system_tokens}, user={user_tokens}, total={total_input_tokens}")

        # 步骤4: 调用OpenAI生成最终答案（流式）
        try:
            response = self.client.responses.create(
                model=self.model,
                input=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": enhanced_prompt}
                ],
                stream=True
            )

            for event in response:
                yield {
                    "status": "stream",
                    "content": event
                }

            yield {
                "status": "final",
                "content": "查询处理结束"
            }
        except Exception as e:
            logger.error(f"OpenAI API 调用失败: {e}")
            yield {
                "type": "error",
                "content": f"抱歉，生成答案时出错: {e}"
            }
    
    async def cleanup(self):
        """清理资源"""
        if self.mcp_client:
            await self.mcp_client.close()
            logger.info("MCP客户端已关闭")
