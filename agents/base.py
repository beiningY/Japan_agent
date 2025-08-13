from abc import ABC, abstractmethod
import os
import json
from dotenv import load_dotenv

class BaseAgent(ABC):
    def __init__(self,
                 temperature: float | None = None,
                 system_message: str | None = None,
                 max_tokens: int | None = None):
        self.custom_temperature = temperature
        self.custom_system_message = system_message
        self.custom_max_tokens = max_tokens
        self.load_config()
        self.load_env()
        self.init_model()

    def load_env(self):
        """加载环境变量"""
        load_dotenv(dotenv_path=".env")
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        self.api_key = os.getenv("GPT_API_KEY")
        if not self.api_key:
            raise ValueError("API_KEY 未在 .env 文件中设置")


    def load_config(self):
        """加载默认配置如果有传入的参数就合并custom参数"""
        config_path = "config/default_config.json"
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)
        
        # 读取默认配置文件的配置
        self.temperature = self.config.get("temperature", 0.4)
        self.system_message = self.config.get("system_message", "默认系统消息")
        self.max_tokens = self.config.get("max_tokens", 4096)
        
        # 如果用户传入了参数就覆盖默认参数
        if self.custom_temperature is not None:
            self.temperature = self.custom_temperature
        if self.custom_system_message is not None:
            self.system_message = self.custom_system_message
        if self.custom_max_tokens is not None:
            self.max_tokens = self.custom_max_tokens

    @abstractmethod
    def init_model(self):
        """初始化模型配置"""
        pass

    @abstractmethod
    def run(self, query: str, **kwargs):
        """执行一次查询"""
        pass


