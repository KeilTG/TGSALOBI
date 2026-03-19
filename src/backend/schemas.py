from pydantic import BaseModel, Field


class NotifyRequest(BaseModel):
    """Тело запроса на отправку уведомления пользователю (от API «Мой колледж»)."""

    chat_id: str = Field(description="Telegram chat_id пользователя")
    text: str = Field(description="Текст уведомления")
    files_urls: list[str] | None = Field(
        default=None,
        description="URL файлов (документ/фото). Если задан - отправляется как документы с подписью text.",
    )
    link_url: str | None = Field(
        default=None,
        description="URL для вставки в текст кликабельной ссылкой с подписью «Ссылка на пост».",
    )
