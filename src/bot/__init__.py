from src.bot.bot import bot, dp

import src.bot.handlers  # Регистрация обработчиков

__all__ = (
    "bot",
    "dp",
)
from src.bot.bot import bot, dp

# Импортируем обработчики (важно: после создания bot и dp)
import src.bot.handlers

__all__ = (
    "bot",
    "dp",
)