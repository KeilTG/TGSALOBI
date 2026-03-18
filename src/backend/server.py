import html as html_lib
import os
from contextlib import asynccontextmanager
from urllib.parse import urlparse
import logging
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import httpx
from aiogram.types import (
    BufferedInputFile,
    InputMediaPhoto,
    Update,
    URLInputFile,
)
from aiogram.exceptions import TelegramBadRequest
from aiogram.enums import ParseMode
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.bot import bot, dp
from src.backend.dependencies import verify_bot_token
from src.backend.schemas import NotifyRequest

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}

# Заголовок для запросов к API колледжа (скачивание файлов)
_API_HEADERS = {
    settings.TELEGRAM_BOT_TOKEN_ALIAS: settings.TELEGRAM_BOT_TOKEN,
}


def _build_notify_text(text: str, link_url: str | None) -> str:
    """Текст уведомления: text без экранирования. При link_url добавляем ссылку «Ссылка на пост»."""
    if link_url:
        safe_url = html_lib.escape(link_url)
        text = f'{text}\n\n<a href="{safe_url}">🔗 Ссылка на пост</a>'
    return text


def _resolve_url(url: str) -> str:
    """Относительный URL превращаем в абсолютный (база — API колледжа)."""
    url = url.strip()
    if url.startswith("http://") or url.startswith("https://"):
        return url
    base = settings.COLLEGE_API_BASE_URL.rstrip("/")
    return f"{base}/{url.lstrip('/')}"


def _filename_from_url(url: str) -> str:
    """Имя файла из пути URL (например .../news/uuid.pdf → uuid.pdf)."""
    path = urlparse(url).path
    name = path.rstrip("/").split("/")[-1]
    return name or "file"


async def _download_document(url: str) -> tuple[bytes, str]:
    """Скачать файл с API колледжа, вернуть (bytes, filename)."""
    resolved = _resolve_url(url)
    async with httpx.AsyncClient(timeout=30.0, headers=_API_HEADERS) as client:
        resp = await client.get(resolved)
        resp.raise_for_status()
        data = resp.content
    filename = _filename_from_url(resolved)
    return (data, filename)


# Настраиваем вебхук при создании инстанса FastAPI клиента (если включён)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # В режиме разработки можно не настраивать вебхук
    if settings.WEBHOOK_BASE_URL != 'https://your-domain.com':
        webhook_url = f"{settings.WEBHOOK_BASE_URL.rstrip('/')}{settings.WEBHOOK_PATH}"
        await bot.set_webhook(
            url=webhook_url,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True,
        )
        logger.info(f"Webhook set to {webhook_url}")
    else:
        logger.info("Webhook not configured (using polling mode)")
    yield
    if settings.WEBHOOK_BASE_URL != 'https://your-domain.com':
        await bot.delete_webhook()
        logger.info("Webhook deleted")


app = FastAPI(lifespan=lifespan)

# Добавляем CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Корневой эндпоинт для проверки
@app.get("/")
async def root():
    return {"status": "ok", "message": "Telegram Bot API is running"}


# Вебхук для Telegram бота (если используется)
@app.post(settings.WEBHOOK_PATH)
async def webhook(request: Request):
    body = await request.json()
    logger.info(f"Received webhook update: {body.get('update_id')}")
    update = Update.model_validate(body, context={"bot": bot})
    await dp.feed_webhook_update(bot=bot, update=update)
    return {"ok": True}


@app.post("/notify", status_code=204)
async def notify_user(
    body: NotifyRequest,
    _: None = Depends(verify_bot_token),
):
    logger.info(f"Sending notification to chat_id: {body.chat_id}")
    chat_id = int(body.chat_id)
    text = _build_notify_text(body.text, body.link_url)

    if not body.files_urls:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.HTML,
        )
        return

    image_urls: list[str] = []
    document_urls: list[str] = []
    for url in body.files_urls:
        ext = os.path.splitext(url)[1].lower()
        if ext in IMAGE_EXTENSIONS:
            image_urls.append(url)
        else:
            document_urls.append(url)

    # 1) Изображения — одним сообщением с текстом (caption)
    if image_urls:
        resolved_image_urls = [_resolve_url(u) for u in image_urls]
        try:
            if len(resolved_image_urls) == 1:
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=URLInputFile(resolved_image_urls[0]),
                    caption=text,
                    parse_mode=ParseMode.HTML,
                )
            else:
                media = [
                    InputMediaPhoto(media=URLInputFile(u)) for u in resolved_image_urls
                ]
                media[0].caption = text
                media[0].parse_mode = ParseMode.HTML
                await bot.send_media_group(chat_id=chat_id, media=media)
        except TelegramBadRequest as e:
            logger.error(f"Error sending photos: {e}")
            await bot.send_message(
                chat_id=chat_id, text=text, parse_mode=ParseMode.HTML
            )
            for u in resolved_image_urls:
                try:
                    await bot.send_photo(chat_id=chat_id, photo=URLInputFile(u))
                except Exception as e:
                    logger.error(f"Error sending photo {u}: {e}")
    elif not document_urls:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)
        return
    else:
        # Только вложения — сначала текст, потом файлы
        await bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)

    # 2) Вложения — отдельными сообщениями, скачиваем с API и задаём имя файла
    for url in document_urls:
        try:
            data, filename = await _download_document(url)
            doc = BufferedInputFile(file=data, filename=filename)
            await bot.send_document(
                chat_id=chat_id,
                document=doc,
            )
        except (httpx.HTTPError, TelegramBadRequest) as e:
            logger.error(f"Error downloading/sending document {url}: {e}")
            # Fallback: отправить по URL (без гарантии имени)
            try:
                await bot.send_document(
                    chat_id=chat_id,
                    document=URLInputFile(_resolve_url(url)),
                )
            except Exception as e:
                logger.error(f"Error sending document via URL {url}: {e}")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    logger.info(f"Starting server on {settings.SERVER_HOST}:{settings.SERVER_PORT}")
    uvicorn.run(
        "src.backend.server:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.DEBUG,
        log_level="info"
    )