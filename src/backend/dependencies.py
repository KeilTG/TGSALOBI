from fastapi import Header, HTTPException
from src.core.config import settings


def verify_bot_token(
    header: str | None = Header(alias=settings.TELEGRAM_BOT_TOKEN_ALIAS, default=None),
) -> None:
    """Проверка токена: вызывать может только API сервиса «Мой колледж»."""
    if header != settings.TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid bot token")
