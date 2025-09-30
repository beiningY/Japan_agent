# run_flow.py
"""
Flow运行入口 - 多智能体协作规划执行

基于OpenManus的flow架构，整合Camel_agent项目的智能体
"""

from __future__ import annotations
import asyncio
import logging
import os
import sys
import time
from typing import Dict, Optional, Any
import argparse

# 确保项目根目录在sys.path中
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# 导入flow相关模块
from flow import FlowFactory, FlowType
from flow.base import create_camel_agent_wrapper

# 导入现有的agent
try:
    from agents.data_agent import DataAgent
    from agents.mcp_toolcall_agent import MCPToolCallAgent
except ImportError as e:
    print(f"导入agent失败: {e}")
    sys.exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FlowRunner:
    """Flow运行器 - 管理多智能体协作执行"""

    def __init__(self):
        self.agents: Dict[str, Any] = {}
        self.flow = None

    async def setup_agents(self, config: Optional[Dict[str, Any]] = None) -> None:
        """设置和初始化智能体"""

        config = config or {}

        # 创建DataAgent
        try:
            data_agent_config = config.get("data_agent", {})
            data_agent = DataAgent(
                system_prompt=data_agent_config.get(
                    "system_prompt",
                    "你是数据获取与分析助手。优先使用工具获取知识库与数据库的真实数据，回答时请标注来源。"
                ),
                max_steps=data_agent_config.get("max_steps", 10)
            )

            # 包装为flow兼容的agent
            wrapped_data_agent = create_camel_agent_wrapper(
                name="data_agent",
                agent_instance=data_agent,
                description="数据分析和知识库查询专家，擅长使用工具获取和分析数据"
            )

            self.agents["data_agent"] = wrapped_data_agent
            logger.info("DataAgent 初始化成功")

        except Exception as e:
            logger.error(f"DataAgent 初始化失败: {e}")

        # 创建通用MCPToolCallAgent
        try:
            mcp_agent_config = config.get("mcp_agent", {})
            mcp_agent = MCPToolCallAgent(
                system_prompt=mcp_agent_config.get(
                    "system_prompt",
                    "你是工具调用助手。根据任务需求使用合适的工具来完成任务。"
                ),
                max_steps=mcp_agent_config.get("max_steps", 10)
            )

            wrapped_mcp_agent = create_camel_agent_wrapper(
                name="mcp_agent",
                agent_instance=mcp_agent,
                description="通用工具调用助手，可以执行各种MCP工具操作"
            )

            self.agents["mcp_agent"] = wrapped_mcp_agent
            logger.info("MCPToolCallAgent 初始化成功")

        except Exception as e:
            logger.error(f"MCPToolCallAgent 初始化失败: {e}")

        if not self.agents:
            raise RuntimeError("没有成功初始化任何智能体")

        logger.info(f"共初始化 {len(self.agents)} 个智能体: {list(self.agents.keys())}")

    async def create_flow(
        self,
        flow_type: FlowType = FlowType.PLANNING,
        primary_agent: Optional[str] = None,
        **kwargs
    ) -> None:
        """创建执行流程"""

        if not self.agents:
            raise RuntimeError("请先初始化智能体")

        # 设置主要智能体
        if not primary_agent:
            primary_agent = "data_agent" if "data_agent" in self.agents else next(iter(self.agents))

        # 创建flow
        self.flow = FlowFactory.create_flow(
            flow_type=flow_type,
            agents=self.agents,
            primary_agent_key=primary_agent,
            **kwargs
        )

        logger.info(f"Flow创建成功，类型: {flow_type.value}, 主要智能体: {primary_agent}")

    async def execute_task(self, prompt: str) -> str:
        """执行任务"""

        if not self.flow:
            raise RuntimeError("请先创建Flow")

        logger.info(f"开始执行任务: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")

        try:
            start_time = time.time()
            result = await asyncio.wait_for(
                self.flow.execute(prompt),
                timeout=1800  # 30分钟超时
            )
            elapsed_time = time.time() - start_time

            logger.info(f"任务执行完成，耗时 {elapsed_time:.2f} 秒")
            return result

        except asyncio.TimeoutError:
            logger.error("任务执行超时")
            return "任务执行超时，请尝试简化任务或增加超时时间。"
        except Exception as e:
            logger.error(f"任务执行失败: {e}")
            return f"任务执行失败: {str(e)}"

    async def cleanup(self) -> None:
        """清理资源"""

        if self.flow:
            await self.flow.cleanup()

        for agent_name, agent in self.agents.items():
            try:
                await agent.cleanup()
                logger.info(f"Agent {agent_name} 清理完成")
            except Exception as e:
                logger.warning(f"清理 Agent {agent_name} 时出错: {e}")


async def run_flow_interactive():
    """交互式运行flow"""

    runner = FlowRunner()

    try:
        print("🚀 初始化多智能体协作系统...")

        # 设置智能体
        await runner.setup_agents()

        # 创建flow
        await runner.create_flow()

        print(f"✅ 系统初始化完成，可用智能体: {list(runner.agents.keys())}")
        print("💡 输入任务描述，系统将自动创建计划并执行")
        print("💡 输入 'quit' 或 'exit' 退出\n")

        while True:
            try:
                prompt = input("🤖 请输入任务: ").strip()

                if not prompt:
                    continue

                if prompt.lower() in ['quit', 'exit', '退出']:
                    print("👋 再见!")
                    break

                print("\n🔄 处理中...")
                result = await runner.execute_task(prompt)

                print("\n" + "="*60)
                print("📋 执行结果:")
                print("="*60)
                print(result)
                print("="*60 + "\n")

            except KeyboardInterrupt:
                print("\n⚠️ 任务被中断")
                continue
            except Exception as e:
                print(f"\n❌ 执行出错: {e}")
                continue

    except KeyboardInterrupt:
        print("\n👋 程序已退出")
    except Exception as e:
        print(f"❌ 系统错误: {e}")
    finally:
        await runner.cleanup()


async def run_flow_single(prompt: str, config: Optional[Dict[str, Any]] = None) -> str:
    """单次执行flow"""

    runner = FlowRunner()

    try:
        await runner.setup_agents(config)
        await runner.create_flow()
        result = await runner.execute_task(prompt)
        return result
    finally:
        await runner.cleanup()


def ensure_api_key_env() -> None:
    """确保环境变量中有API密钥"""
    if not (os.environ.get("OPENAI_API_KEY") or os.environ.get("GPT_API_KEY")):
        raise EnvironmentError(
            "未检测到 OPENAI_API_KEY 或 GPT_API_KEY 环境变量，请先设置后再运行。"
        )


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="多智能体协作Flow执行器"
    )
    parser.add_argument(
        "--prompt",
        type=str,
        help="直接执行的任务描述（非交互模式）"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        default=True,
        help="交互模式（默认）"
    )
    parser.add_argument(
        "--collection",
        type=str,
        default="japan_shrimp",
        help="默认知识库名称"
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=10,
        help="每个智能体的最大执行步数"
    )

    return parser.parse_args()


async def main():
    """主函数"""

    try:
        # 确保API密钥存在
        ensure_api_key_env()

        # 解析参数
        args = parse_args()

        # 构建配置
        config = {
            "data_agent": {
                "system_prompt": (
                    f"你是数据获取与分析助手。优先使用工具获取知识库与数据库的真实数据；"
                    f"若未特别说明，默认知识库为 '{args.collection}'；回答中请标注来源。"
                ),
                "max_steps": args.max_steps
            },
            "mcp_agent": {
                "max_steps": args.max_steps
            }
        }

        if args.prompt:
            # 非交互模式，直接执行
            print(f"🚀 执行任务: {args.prompt}")
            result = await run_flow_single(args.prompt, config)
            print("\n" + "="*60)
            print("📋 执行结果:")
            print("="*60)
            print(result)
            print("="*60)
        else:
            # 交互模式
            await run_flow_interactive()

    except KeyboardInterrupt:
        print("\n👋 程序已退出")
    except Exception as e:
        print(f"❌ 程序错误: {e}")
        return 1

    return 0


if __name__ == "__main__":
    import dotenv
    dotenv.load_dotenv()  # 加载.env文件

    exit_code = asyncio.run(main())
    sys.exit(exit_code)