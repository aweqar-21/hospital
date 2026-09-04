"""日志配置 —— 带请求 ID 追踪的结构化日志。"""
import sys
import uuid
from contextvars import ContextVar
from typing import Optional

from loguru import logger

from config.settings import get_settings

# 请求级上下文：用于在单次请求中传递 request_id
request_id_var: ContextVar[str] = ContextVar("request_id", default="")

# 移除默认 handler
logger.remove()


def setup_logger(log_level: Optional[str] = None) -> None:
    """初始化全局日志配置（在应用启动时调用）。"""
    settings = get_settings()
    level = log_level or settings.LOG_LEVEL

    # 控制台输出（彩色）
    logger.add(
        sys.stderr,
        level=level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{extra[request_id]}</cyan> | "
            "<level>{message}</level>"
        ),
        filter=lambda r: r["extra"].get("request_id") != "",
    )

    # 标准输出（不带颜色，用于容器日志）
    logger.add(
        sys.stdout,
        level=level,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {extra[request_id]} | {message}",
    )

    # 文件日志（按日轮转）
    logger.add(
        "logs/chatbot_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        rotation="00:00",
        retention="30 days",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {extra[request_id]} | {message}",
    )


def get_logger():
    """获取 logger 实例。"""
    return logger


def set_request_id(request_id: str = "") -> str:
    """设置当前请求的 request_id。"""
    if not request_id:
        request_id = uuid.uuid4().hex[:12]
    request_id_var.set(request_id)
    return request_id
