#!/usr/bin/env python3
"""
OpenAI 对话客户端脚本
功能：
1. 支持历史记录管理的对话
2. 统计每次请求到响应的时间
3. 错误处理和重试机制
4. Token使用量统计
5. 完整的日志记录

作者：AI Assistant
创建时间：2024
"""

import os
import json
import time
import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
import logging
from pathlib import Path

import openai
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import tiktoken


@dataclass
class ChatMessage:
    """聊天消息数据类"""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: float
    token_count: int = 0


@dataclass
class RequestStats:
    """请求统计数据类"""
    request_time: float
    response_time: float
    duration: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model: str
    success: bool
    error_message: Optional[str] = None


class ChatHistoryManager:
    """聊天历史记录管理器"""
    
    def __init__(self, history_file: str = "chat_history.json"):
        """
        初始化历史记录管理器
        
        Args:
            history_file: 历史记录文件路径
        """
        self.history_file = Path(history_file)
        self.messages: List[ChatMessage] = []
        self.load_history()
    
    def add_message(self, role: str, content: str, token_count: int = 0) -> None:
        """
        添加消息到历史记录
        
        Args:
            role: 消息角色
            content: 消息内容
            token_count: Token数量
        """
        message = ChatMessage(
            role=role,
            content=content,
            timestamp=time.time(),
            token_count=token_count
        )
        self.messages.append(message)
        self.save_history()
    
    def get_messages(self, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """
        获取历史消息，格式化为OpenAI API格式
        
        Args:
            limit: 限制返回的消息数量
            
        Returns:
            格式化的消息列表
        """
        messages = self.messages[-limit:] if limit else self.messages
        return [{"role": msg.role, "content": msg.content} for msg in messages]
    
    def clear_history(self) -> None:
        """清空历史记录"""
        self.messages = []
        self.save_history()
    
    def save_history(self) -> None:
        """保存历史记录到文件"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump([asdict(msg) for msg in self.messages], f, 
                         ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"保存历史记录失败: {e}")
    
    def load_history(self) -> None:
        """从文件加载历史记录"""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.messages = [ChatMessage(**msg) for msg in data]
                logging.info(f"加载了 {len(self.messages)} 条历史消息")
        except Exception as e:
            logging.error(f"加载历史记录失败: {e}")
            self.messages = []


class TokenCounter:
    """Token计数器"""
    
    def __init__(self, model: str = "gpt-4o"):
        """
        初始化Token计数器
        
        Args:
            model: 使用的模型名称
        """
        self.model = model
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            # 如果模型不支持，使用默认编码
            self.encoding = tiktoken.get_encoding("cl100k_base")
    
    def count_tokens(self, text: str) -> int:
        """
        计算文本的Token数量
        
        Args:
            text: 要计算的文本
            
        Returns:
            Token数量
        """
        return len(self.encoding.encode(text))
    
    def count_messages_tokens(self, messages: List[Dict[str, str]]) -> int:
        """
        计算消息列表的总Token数量
        
        Args:
            messages: 消息列表
            
        Returns:
            总Token数量
        """
        total_tokens = 0
        for message in messages:
            # 每条消息的基础Token开销
            total_tokens += 4  # 每条消息的格式开销
            for key, value in message.items():
                total_tokens += self.count_tokens(value)
        total_tokens += 2  # 对话的结束Token
        return total_tokens


class OpenAIChatClient:
    """OpenAI 聊天客户端"""
    
    def __init__(self, 
                 api_key: Optional[str] = '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'
,
                 base_url: Optional[str] = None,
                 model: str = "gpt-4o",
                 max_history: int = 50,
                 stats_file: str = "request_stats.json"):
        """
        初始化OpenAI聊天客户端
        
        Args:
            api_key: OpenAI API密钥
            base_url: API基础URL
            model: 使用的模型
            max_history: 最大历史记录数量
            stats_file: 统计数据文件路径
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = model
        self.max_history = max_history
        self.stats_file = Path(stats_file)
        
        # 初始化客户端
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        # 初始化组件
        self.history_manager = ChatHistoryManager()
        self.token_counter = TokenCounter(model)
        self.request_stats: List[RequestStats] = []
        
        # 设置日志
        self._setup_logging()
        
        # 加载统计数据
        self.load_stats()
    
    def _setup_logging(self) -> None:
        """设置日志配置"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('openai_chat.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((openai.RateLimitError, openai.APITimeoutError))
    )
    async def _make_request(self, messages: List[Dict[str, str]], **kwargs) -> Any:
        """
        发送请求到OpenAI API（带重试机制）
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数
            
        Returns:
            API响应
        """
        return await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            **kwargs
        )
    
    async def chat(self, 
                   user_input: str, 
                   system_prompt: Optional[str] = None,
                   **kwargs) -> str:
        """
        进行对话
        
        Args:
            user_input: 用户输入
            system_prompt: 系统提示（可选）
            **kwargs: 其他OpenAI API参数
            
        Returns:
            AI回复内容
        """
        request_start_time = time.time()
        
        try:
            # 准备消息列表
            messages = []
            
            # 添加系统提示
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            # 添加历史记录
            history_messages = self.history_manager.get_messages(self.max_history)
            messages.extend(history_messages)
            
            # 添加当前用户输入
            messages.append({"role": "user", "content": user_input})
            
            # 计算输入Token数量
            prompt_tokens = self.token_counter.count_messages_tokens(messages)
            user_tokens = self.token_counter.count_tokens(user_input)
            
            self.logger.info(f"发送请求 - 模型: {self.model}, Prompt Tokens: {prompt_tokens}")
            
            # 发送请求
            response = await self._make_request(messages, **kwargs)
            
            request_end_time = time.time()
            duration = request_end_time - request_start_time
            
            # 提取响应内容
            assistant_message = response.choices[0].message.content
            
            # 获取Token使用统计
            usage = response.usage
            completion_tokens = usage.completion_tokens if usage else 0
            total_tokens = usage.total_tokens if usage else 0
            
            # 计算助手回复的Token数量
            assistant_tokens = self.token_counter.count_tokens(assistant_message)
            
            # 记录统计信息
            stats = RequestStats(
                request_time=request_start_time,
                response_time=request_end_time,
                duration=duration,
                prompt_tokens=usage.prompt_tokens if usage else prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                model=self.model,
                success=True
            )
            self.request_stats.append(stats)
            
            # 保存到历史记录
            self.history_manager.add_message("user", user_input, user_tokens)
            self.history_manager.add_message("assistant", assistant_message, assistant_tokens)
            
            # 保存统计数据
            self.save_stats()
            
            # 记录成功日志
            self.logger.info(
                f"请求成功 - 耗时: {duration:.2f}s, "
                f"Tokens: {usage.prompt_tokens if usage else prompt_tokens}/"
                f"{completion_tokens}/{total_tokens}"
            )
            
            return assistant_message
            
        except Exception as e:
            request_end_time = time.time()
            duration = request_end_time - request_start_time
            
            # 记录错误统计
            error_stats = RequestStats(
                request_time=request_start_time,
                response_time=request_end_time,
                duration=duration,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                model=self.model,
                success=False,
                error_message=str(e)
            )
            self.request_stats.append(error_stats)
            self.save_stats()
            
            self.logger.error(f"请求失败 - 耗时: {duration:.2f}s, 错误: {e}")
            raise
    
    def get_stats_summary(self) -> Dict[str, Any]:
        """
        获取统计摘要
        
        Returns:
            统计摘要字典
        """
        if not self.request_stats:
            return {"message": "暂无统计数据"}
        
        successful_requests = [s for s in self.request_stats if s.success]
        failed_requests = [s for s in self.request_stats if not s.success]
        
        total_requests = len(self.request_stats)
        success_rate = len(successful_requests) / total_requests * 100
        
        if successful_requests:
            avg_duration = sum(s.duration for s in successful_requests) / len(successful_requests)
            total_tokens = sum(s.total_tokens for s in successful_requests)
            avg_tokens = total_tokens / len(successful_requests)
        else:
            avg_duration = 0
            total_tokens = 0
            avg_tokens = 0
        
        return {
            "总请求数": total_requests,
            "成功请求数": len(successful_requests),
            "失败请求数": len(failed_requests),
            "成功率": f"{success_rate:.1f}%",
            "平均响应时间": f"{avg_duration:.2f}秒",
            "总Token使用量": total_tokens,
            "平均Token使用量": f"{avg_tokens:.0f}",
            "使用模型": self.model
        }
    
    def save_stats(self) -> None:
        """保存统计数据到文件"""
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump([asdict(stat) for stat in self.request_stats], f, 
                         ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存统计数据失败: {e}")
    
    def load_stats(self) -> None:
        """从文件加载统计数据"""
        try:
            if self.stats_file.exists():
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.request_stats = [RequestStats(**stat) for stat in data]
                self.logger.info(f"加载了 {len(self.request_stats)} 条统计记录")
        except Exception as e:
            self.logger.error(f"加载统计数据失败: {e}")
            self.request_stats = []
    
    def clear_history(self) -> None:
        """清空聊天历史"""
        self.history_manager.clear_history()
        self.logger.info("聊天历史已清空")
    
    def clear_stats(self) -> None:
        """清空统计数据"""
        self.request_stats = []
        self.save_stats()
        self.logger.info("统计数据已清空")


async def interactive_chat():
    """交互式聊天函数"""
    print("🤖 OpenAI 聊天客户端")
    print("=" * 50)
    print("输入 'quit' 或 'exit' 退出")
    print("输入 'clear' 清空历史记录")
    print("输入 'stats' 查看统计信息")
    print("=" * 50)
    
    # 初始化客户端
    client = OpenAIChatClient()
    
    # 检查API密钥
    if not client.api_key:
        print("❌ 错误: 未设置 OPENAI_API_KEY 环境变量")
        return
    
    print(f"✅ 使用模型: {client.model}")
    print(f"📚 历史记录: {len(client.history_manager.messages)} 条消息")
    print()
    
    while True:
        try:
            user_input = input("👤 您: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit']:
                print("👋 再见!")
                break
            
            if user_input.lower() == 'clear':
                client.clear_history()
                print("🗑️ 历史记录已清空")
                continue
            
            if user_input.lower() == 'stats':
                stats = client.get_stats_summary()
                print("\n📊 统计信息:")
                for key, value in stats.items():
                    print(f"  {key}: {value}")
                print()
                continue
            
            # 发送请求并计时
            start_time = time.time()
            print("🤔 思考中...")
            
            response = await client.chat(user_input)
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"🤖 AI ({duration:.2f}s): {response}")
            print()
            
        except KeyboardInterrupt:
            print("\n👋 再见!")
            break
        except Exception as e:
            print(f"❌ 错误: {e}")
            print()


async def main():
    """主函数"""
    await interactive_chat()


if __name__ == "__main__":
    asyncio.run(main())