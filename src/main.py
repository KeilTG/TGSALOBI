import sys
import os
import asyncio
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.config import settings
from src.bot import bot, dp
import src.bot.handlers

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def main():
    """Запуск бота"""
    logger.info("Starting bot...")
    logger.info(f"Bot token: {settings.BOT_TOKEN[:10]}...")
    logger.info(f"Admin ID: 1117420621")
    
    # Удаляем вебхук
    await bot.delete_webhook()
    
    # Запускаем polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")