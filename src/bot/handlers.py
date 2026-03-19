from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging
import asyncio

from src.bot.bot import dp, bot
from src.database import add_user, get_all_users, get_user_settings, update_user_settings

logger = logging.getLogger(__name__)

# Состояния
class FeedbackStates(StatesGroup):
    waiting_for_feedback = State()
    waiting_for_admin_reply = State()

ADMIN_ID = 1117420621
CHANNEL_ID = -1003757065850


# ================ КЛАВИАТУРА ДЛЯ HELP ================
def get_help_keyboard(user_id: int = None):
    """Клавиатура для команды /help"""
    keyboard = []
    
    # Кнопка для жалобы
    keyboard.append([InlineKeyboardButton(text="📝 Написать об ошибке", callback_data="write_error")])
    
    # Кнопка для уведомлений
    if user_id:
        settings = get_user_settings(user_id)
        notif_enabled = settings.get('notifications_enabled', True)
        status = "🔔 Включены" if notif_enabled else "🔕 Выключены"
        keyboard.append([InlineKeyboardButton(
            text=f"Уведомления: {status}", 
            callback_data="toggle_notifications"
        )])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================ КОМАНДА START ================
@dp.message(CommandStart())
async def start_command(message: Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name
    
    # Сохраняем пользователя
    add_user(user_id, username, full_name)
    logger.info(f"User {user_id} saved")
    
    if user_id == ADMIN_ID:
        # Текст для администратора (как ты просил)
        await message.answer(
            "👋 Здравствуйте, администратор!\n\n"
            "Бот добавлен в канал и будет пересылать новые посты всем пользователям.\n"
            "Также вы будете получать уведомления о новых жалобах.\n\n"
            "Используйте /help для управления настройками."
        )
        return
    
    # Клавиатура для обычных пользователей
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Написать об ошибке", callback_data="write_error")]
        ]
    )
    
    await message.answer(
        "👋 Добро пожаловать!\n\n"
        "Если вы нашли ошибку - нажмите кнопку ниже.\n"
        "Новости колледжа будут приходить вам автоматически.",
        reply_markup=keyboard
    )


# ================ КОМАНДА HELP ================
@dp.message(Command("help"))
async def help_command(message: Message):
    """Обработчик команды /help"""
    user_id = message.from_user.id
    
    await message.answer(
        "📋 <b>Меню помощи</b>\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=get_help_keyboard(user_id)
    )


# ================ ОБРАБОТЧИКИ КНОПОК ================
@dp.callback_query(lambda c: c.data == "write_error")
async def process_write_error(callback_query, state: FSMContext):
    """Кнопка 'Написать об ошибке'"""
    await callback_query.answer()
    await state.set_state(FeedbackStates.waiting_for_feedback)
    
    await callback_query.message.edit_text(
        "📝 Опишите проблему или ошибку:\n\n"
        "(для отмены отправьте /cancel)"
    )


@dp.callback_query(lambda c: c.data == "toggle_notifications")
async def toggle_notifications(callback_query):
    """Кнопка включения/выключения уведомлений"""
    user_id = callback_query.from_user.id
    
    # Получаем текущие настройки
    settings = get_user_settings(user_id)
    current = settings.get('notifications_enabled', True)
    
    # Меняем значение
    new_value = not current
    update_user_settings(user_id, {'notifications_enabled': new_value})
    
    status = "включены" if new_value else "выключены"
    await callback_query.answer(f"Уведомления {status}")
    
    # Обновляем сообщение
    await callback_query.message.edit_text(
        "📋 <b>Меню помощи</b>\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=get_help_keyboard(user_id)
    )


# ================ ОБРАБОТКА ЖАЛОБ ================
@dp.message(FeedbackStates.waiting_for_feedback)
async def process_feedback(message: Message, state: FSMContext):
    """Получение текста жалобы от пользователя"""
    user = message.from_user
    feedback_text = message.text
    
    logger.info(f"Feedback from user {user.id}")
    
    # Кнопка для ответа админу
    reply_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="✏️ Ответить на заявку", 
                callback_data=f"reply_to_{user.id}"
            )]
        ]
    )
    
    # Сообщение админу
    admin_msg = (
        f"⚠️ <b>НОВАЯ ЖАЛОБА</b>\n\n"
        f"<b>От:</b> {user.full_name}\n"
        f"<b>Username:</b> @{user.username or 'нет'}\n"
        f"<b>ID:</b> <code>{user.id}</code>\n"
        f"<b>Сообщение:</b>\n{feedback_text}"
    )
    
    try:
        # Отправляем админу
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_msg,
            parse_mode="HTML",
            reply_markup=reply_keyboard
        )
        
        # Подтверждение пользователю
        await message.answer("✅ Ваше сообщение отправлено администратору!\nОжидайте ответа.")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await message.answer("❌ Ошибка отправки. Попробуйте позже.")
    
    await state.clear()


# ================ ОТВЕТЫ АДМИНА ================
@dp.callback_query(lambda c: c.data.startswith("reply_to_"))
async def process_admin_reply_start(callback_query, state: FSMContext):
    """Админ нажал кнопку ответа"""
    await callback_query.answer()
    
    user_id = int(callback_query.data.replace("reply_to_", ""))
    await state.update_data(reply_to_user_id=user_id)
    await state.set_state(FeedbackStates.waiting_for_admin_reply)
    
    await callback_query.message.answer(
        f"✏️ Напишите ответ для пользователя (ID: {user_id}):\n"
        "(для отмены отправьте /cancel)"
    )
    
    # Убираем кнопку под сообщением
    await callback_query.message.edit_reply_markup(reply_markup=None)


@dp.message(FeedbackStates.waiting_for_admin_reply)
async def process_admin_reply(message: Message, state: FSMContext):
    """Админ отправляет ответ"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет прав")
        await state.clear()
        return
    
    data = await state.get_data()
    user_id = data.get("reply_to_user_id")
    
    if not user_id:
        await message.answer("Ошибка")
        await state.clear()
        return
    
    try:
        # Отправляем ответ пользователю
        await bot.send_message(
            chat_id=user_id,
            text=f"✉️ <b>Ответ администратора:</b>\n\n{message.text}",
            parse_mode="HTML"
        )
        
        await message.answer(f"✅ Ответ отправлен пользователю {user_id}")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await message.answer("❌ Не удалось отправить ответ")
    
    await state.clear()


# ================ ПЕРЕСЫЛКА ИЗ КАНАЛА ================
@dp.channel_post()
async def handle_channel_post(message: Message):
    """Пересылка постов из канала"""
    logger.info(f"New post in channel")
    
    users = get_all_users()
    
    for user_id in users:
        try:
            # Проверяем настройки
            settings = get_user_settings(user_id)
            if not settings.get('notifications_enabled', True):
                continue
                
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id=CHANNEL_ID,
                message_id=message.message_id
            )
            await asyncio.sleep(0.05)
            
        except Exception as e:
            logger.error(f"Error forwarding to {user_id}: {e}")


# ================ ВСПОМОГАТЕЛЬНОЕ ================
@dp.message(lambda message: message.text == "/cancel")
async def cancel(message: Message, state: FSMContext):
    """Отмена действия"""
    await state.clear()
    await message.answer("Действие отменено")


@dp.message()
async def unknown(message: Message):
    """Неизвестные команды"""
    await message.answer("Нажмите /start для начала работы")