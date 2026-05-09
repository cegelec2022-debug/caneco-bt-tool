import sys

from loguru import logger

from app.core.config import settings


def configure_logging() -> None:
    logger.remove()

    level = "DEBUG" if not settings.is_production else "INFO"
    fmt = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
        "<level>{message}</level>"
    )
    logger.add(sys.stderr, format=fmt, level=level, colorize=True)

    if settings.is_production:
        logger.add(
            "logs/caneco_bt.log",
            rotation="100 MB",
            retention="30 days",
            level="INFO",
            format="{time} | {level} | {name}:{function}:{line} — {message}",
        )
