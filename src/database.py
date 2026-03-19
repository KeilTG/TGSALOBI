import sqlite3
from datetime import datetime
import json

DB_PATH = "bot_database.db"

def init_db():
    """Создает таблицы при первом запуске"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Удаляем старую таблицу если есть (чтобы точно обновить структуру)
    cursor.execute('DROP TABLE IF EXISTS users')
    
    # Создаем новую таблицу с колонкой settings
    cursor.execute('''
        CREATE TABLE users (
            chat_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            registered_at TIMESTAMP,
            settings TEXT DEFAULT '{"notifications_enabled": true}'
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized with settings column")

def add_user(chat_id, username, full_name):
    """Добавляет или обновляет пользователя"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Проверяем, есть ли пользователь
    cursor.execute('SELECT chat_id FROM users WHERE chat_id = ?', (chat_id,))
    existing = cursor.fetchone()
    
    if existing:
        # Обновляем существующего
        cursor.execute('''
            UPDATE users 
            SET username = ?, full_name = ?
            WHERE chat_id = ?
        ''', (username, full_name, chat_id))
    else:
        # Добавляем нового с настройками по умолчанию
        default_settings = json.dumps({"notifications_enabled": True})
        cursor.execute('''
            INSERT INTO users (chat_id, username, full_name, registered_at, settings)
            VALUES (?, ?, ?, datetime('now'), ?)
        ''', (chat_id, username, full_name, default_settings))
    
    conn.commit()
    conn.close()

def get_user_settings(chat_id):
    """Получает настройки пользователя"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT settings FROM users WHERE chat_id = ?', (chat_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result and result[0]:
        return json.loads(result[0])
    return {"notifications_enabled": True}

def update_user_settings(chat_id, settings_dict):
    """Обновляет настройки пользователя"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Получаем текущие настройки
    current = get_user_settings(chat_id)
    current.update(settings_dict)
    
    cursor.execute('''
        UPDATE users 
        SET settings = ?
        WHERE chat_id = ?
    ''', (json.dumps(current), chat_id))
    
    conn.commit()
    conn.close()

def get_all_users():
    """Возвращает список всех chat_id"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT chat_id FROM users')
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users

# Инициализация при импорте
init_db()