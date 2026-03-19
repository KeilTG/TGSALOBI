import httpx
import asyncio
import logging
from datetime import datetime, timedelta
from src.core.config import settings
from src.bot.bot import bot
from src.database import get_all_users, save_last_news_id, get_last_news_id

logger = logging.getLogger(__name__)

class NewsChecker:
    def __init__(self):
        self.last_check = datetime.now() - timedelta(minutes=5)
        self.last_news_id = get_last_news_id()
        self.check_interval = 300  # Проверка каждые 5 минут
        
    async def check_news(self):
        """Проверяет API колледжа на новые новости"""
        try:
            logger.info("Checking for new news...")
            
            headers = {
                settings.TELEGRAM_BOT_TOKEN_ALIAS: settings.TELEGRAM_BOT_TOKEN
            }
            
            async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
                response = await client.get(
                    f"{settings.COLLEGE_API_BASE_URL}/api/news/latest",
                    params={"since": self.last_check.isoformat()}
                )
                
                if response.status_code == 200:
                    news_list = response.json()
                    logger.info(f"Found {len(news_list)} new news items")
                    
                    for news in news_list:
                        if news['id'] > self.last_news_id:
                            await self.send_news_to_users(news)
                            self.last_news_id = news['id']
                            save_last_news_id(news['id'])
                    
                    self.last_check = datetime.now()
                else:
                    logger.warning(f"API returned {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Error checking news: {e}")
    
    async def send_news_to_users(self, news):
        """Отправляет новость всем пользователям"""
        users = get_all_users()
        logger.info(f"Sending news {news['id']} to {len(users)} users")
        
        text = f"📢 <b>{news.get('title', 'Новость')}</b>\n\n{news.get('content', '')}"
        images = news.get('images', [])
        link = news.get('link', '')
        
        for user_id in users:
            try:
                await self.send_via_notify(user_id, text, link, images)
                await asyncio.sleep(0.05)
            except Exception as e:
                logger.error(f"Error sending to {user_id}: {e}")
    
    async def send_via_notify(self, chat_id, text, link, images):
        """Использует существующий /notify эндпоинт"""
        headers = {
            settings.TELEGRAM_BOT_TOKEN_ALIAS: settings.TELEGRAM_BOT_TOKEN
        }
        
        payload = {
            "chat_id": str(chat_id),
            "text": text,
            "files_urls": images if images else None,
            "link_url": link if link else None
        }
        
        async with httpx.AsyncClient() as client:
            await client.post(
                f"http://localhost:{settings.SERVER_PORT}/notify",
                json=payload,
                headers=headers
            )


async def news_checker_loop():
    """Бесконечный цикл проверки новостей"""
    checker = NewsChecker()
    while True:
        await checker.check_news()
        await asyncio.sleep(checker.check_interval)