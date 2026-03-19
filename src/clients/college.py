import httpx
import logging
from src.core.config import settings
from src.clients.exceptions import AlreadyBoundError

logger = logging.getLogger(__name__)


class CollegeClient:
    """Клиент для запросов к внешнему API сервиса "Наш колледж"."""

    def __init__(self, base_url: str | None = None, timeout: float = 15.0) -> None:
        self._base_url = (base_url or settings.COLLEGE_API_BASE_URL).rstrip("/")
        self._timeout = timeout
        self._headers = {
            settings.TELEGRAM_BOT_TOKEN_ALIAS: settings.TELEGRAM_BOT_TOKEN,
        }
        logger.info(f"CollegeClient initialized with base_url: {self._base_url}")

    def _url(self, path: str) -> str:
        return f"{self._base_url}/{path.lstrip('/')}"

    async def get_user_by_chat_id(self, chat_id: int) -> dict | None:
        """
        Получить пользователя по Telegram chat_id (GET /api/telegram/user?chat_id=...).
        Возвращает данные пользователя или None, если не найден (404).
        """
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, headers=self._headers
            ) as client:
                response = await client.get(
                    self._url("api/telegram/user"),
                    params={"chat_id": str(chat_id)},
                )
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                return response.json()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.warning(f"Failed to connect to college API: {e}")
            # Возвращаем тестовые данные для разработки
            if settings.DEBUG:
                return {"id": 1, "chat_id": chat_id, "name": "Test User"}
            return None
        except Exception as e:
            logger.error(f"Unexpected error in get_user_by_chat_id: {e}")
            return None

    async def bind_telegram_by_token(self, token: str, chat_id: int) -> bool:
        """
        Привязать Telegram по токену из ссылки (t.me/bot?start=TOKEN). Возвращает True при успехе (204).
        """
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, headers=self._headers
            ) as client:
                response = await client.post(
                    self._url("api/telegram/bind"),
                    json={
                        "token": token,
                        "chat_id": str(chat_id),
                    },
                )
                if response.status_code == 409:
                    raise AlreadyBoundError("Пользователь уже привязан")
                if response.status_code != 204:
                    raise ValueError("Не удалось привязать Telegram по ссылке")
                return True
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.warning(f"Failed to connect to college API for binding: {e}")
            # Для тестов - считаем что привязка успешна если есть токен
            if settings.DEBUG and token:
                logger.info(f"DEBUG: Simulating successful binding for token: {token[:10]}...")
                return True
            raise ValueError("API колледжа недоступен")

    async def get_file(self, file_url: str) -> bytes | None:
        """
        Получить файл по URL (GET /api/file?url=...). Возвращает содержимое файла.
        """
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, headers=self._headers
            ) as client:
                response = await client.get(
                    self._url("api/file"),
                    params={"url": file_url},
                )
                if response.status_code == 404 or response.status_code == 403:
                    return None
                return response.content
        except Exception as e:
            logger.error(f"Error downloading file {file_url}: {e}")
            return None


college_client = CollegeClient()