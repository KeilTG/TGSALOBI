from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Telegram Bot
    BOT_TOKEN: str = '8452947775:AAEkDMXlKKMPDzATU0zf3Nm4dU0K5JWOooI'
    TELEGRAM_BOT_TOKEN: str = '8452947775:AAEkDMXlKKMPDzATU0zf3Nm4dU0K5JWOooI'
    TELEGRAM_BOT_TOKEN_ALIAS: str = 'X-Telegram-Bot-Token'
    
    # Server settings
    SERVER_HOST: str = '0.0.0.0'
    SERVER_PORT: int = 8000
    
    # Webhook
    WEBHOOK_PATH: str = '/webhook'
    WEBHOOK_BASE_URL: str = 'https://your-domain.com'
    
    # College API
    COLLEGE_API_BASE_URL: str = 'http://localhost:8001'
    
    # Другие настройки
    DEBUG: bool = True
    
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

settings = Settings()