import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager
from ToolOrchestrator.core.registry import ToolRegistry
from ToolOrchestrator.core.config import settings
from ToolOrchestrator.api import endpoint
import uvicorn

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ToolOrchestratorMain")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("工具网关开始启动...")
    registry = ToolRegistry(mcp_client_config=settings.MCP_CLIENT_CONFIG)
    
    await registry.initialize_connections()
    registry.load_from_json(settings.TOOLS_CONFIG_PATH)

    app.state.tool_registry = registry
    print("工具网关启动完毕，开始接受请求...")
    logger.info("工具网关启动完毕，开始接受请求...")
    yield
    print("工具网关已完成服务请求...")
    logger.info("工具网关已完成服务请求...")

app = FastAPI(
    title="工具协调器网关",
    description="一个通过MCP协议协调工具的网关",
    lifespan=lifespan
)

app.include_router(endpoint.router, prefix="/api", tags=["Tools"])

@app.get("/", tags=["Health"])
def read_root():
    return {"status": "ok", "message": "工具协调器网关正在工作"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app", 
        host='0.0.0.0', 
        port=8000,
        reload=True,
        log_level="info"
    )