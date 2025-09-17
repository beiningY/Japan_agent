# core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    TOOLS_CONFIG_PATH: str = "ToolOrchestrator/tools/config.json"
    
    MCP_CLIENT_CONFIG: dict = {
        # --- 原有的db服务配置保持不变 ---
        "db-mcp-server": {
            "command": "python",
            "args": ["ToolOrchestrator/services/db_server.py"],
            "transport": "stdio",
        },
        # --- 新增的kb服务配置 ---
        "kb-mcp-server": {
            "command": "python",
            "args": ["ToolOrchestrator/services/kb_server.py"], 
            "transport": "stdio",
        }
    }

settings = Settings()