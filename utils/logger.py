# utils/logger.py
"""
简洁日志配置 - 显示模块名

使用方法:
    from utils.logger import setup_logging, get_logger

    # 在main.py或项目启动时调用一次
    setup_logging()

    # 在任何模块中使用
    logger = get_logger(__name__)
    logger.info("这条日志会显示模块名")
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(console_level="INFO", file_level="DEBUG"):
    """设置全局日志配置"""

    # 创建logs目录（如果不存在）
    Path("logs").mkdir(exist_ok=True)

    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # 清除现有处理器
    root_logger.handlers.clear()

    # 控制台处理器 - 显示模块名
    console = logging.StreamHandler()
    console.setLevel(getattr(logging, console_level.upper()))
    console.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    ))
    root_logger.addHandler(console)

    # 文件处理器 - 包含详细信息
    file_handler = RotatingFileHandler(
        "logs/app.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setLevel(getattr(logging, file_level.upper()))
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    ))
    root_logger.addHandler(file_handler)

    # 降低第三方库日志级别
    for lib in ['openai', 'httpx', 'urllib3', 'uvicorn']:
        logging.getLogger(lib).setLevel(logging.WARNING)

    logging.info("日志系统初始化完成")


def get_logger(name):
    """获取指定模块的日志器"""
    return logging.getLogger(name)