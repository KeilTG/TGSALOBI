from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging

from src.bot.bot import dp, bot

logger = logging.getLogger(__name__)

# Состояния
class FeedbackStates(StatesGroup):
    waiting_for_feedback = State()  # Ожидание текста жалобы
    waiting_for_admin_reply = State()  # Ожидание ответа админа

# ID администратора (ТВОЙ ID)
ADMIN_ID = 1117420621


@dp.message(CommandStart())
async def start_command(message: Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    logger.info(f"Start command from user {user_id}")
    
    # Если это админ - показываем спецсообщение
    if user_id == ADMIN_ID:
        await message.answer(
            "👋 <b>Здравствуйте, администратор!</b>\n\n"
            "Вы успешно активировали бота. Теперь вы будете получать уведомления о новых жалобах.\n"
            "Чтобы ответить на жалобу - нажмите кнопку под сообщением."
        )
        return
    
    # Для обычных пользователей - кнопка
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Написать об ошибке", callback_data="write_error")]
        ]
    )
    
    await message.answer(
        "👋 Добро пожаловать!\n\n"
        "Если вы нашли ошибку или у вас есть проблема - нажмите кнопку ниже.",
        reply_markup=keyboard
    )


@dp.callback_query(lambda c: c.data == "write_error")
async def process_write_error(callback_query, state: FSMContext):
    """Обработка кнопки 'Написать об ошибке'"""
    await callback_query.answer()
    await state.set_state(FeedbackStates.waiting_for_feedback)
    
    await callback_query.message.edit_text(
        "📝 Опишите проблему или ошибку:\n\n"
        "(для отмены отправьте /cancel)"
    )


@dp.message(FeedbackStates.waiting_for_feedback)
async def process_feedback(message: Message, state: FSMContext):
    """Отправка жалобы админу"""
    user = message.from_user
    feedback_text = message.text
    
    logger.info(f"Feedback from user {user.id}: {feedback_text[:50]}...")
    
    # Создаем кнопку для ответа админу
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
        # Отправляем админу с кнопкой ответа
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_msg,
            parse_mode="HTML",
            reply_markup=reply_keyboard
        )
        
        # Подтверждение пользователю
        await message.answer("✅ Ваше сообщение отправлено администратору!\nОжидайте ответа.")
        logger.info(f"Feedback sent to admin {ADMIN_ID}")
        
    except Exception as e:
        logger.error(f"Error sending to admin: {e}")
        await message.answer(
            "❌ Не удалось отправить. Администратор еще не активировал бота.\n"
            "Пожалуйста, попробуйте позже."
        )
    
    await state.clear()


@dp.callback_query(lambda c: c.data.startswith("reply_to_"))
async def process_admin_reply_start(callback_query, state: FSMContext):
    """Админ нажал кнопку ответа на заявку"""
    await callback_query.answer()
    
    # Извлекаем ID пользователя из callback_data
    user_id = int(callback_query.data.replace("reply_to_", ""))
    
    # Сохраняем ID пользователя в состоянии
    await state.update_data(reply_to_user_id=user_id)
    await state.set_state(FeedbackStates.waiting_for_admin_reply)
    
    # Отправляем сообщение админу с просьбой ввести ответ
    await callback_query.message.answer(
        f"✏️ Напишите ответ для пользователя (ID: {user_id}):\n"
        "(для отмены отправьте /cancel)"
    )
    
    # Можно также отметить, что на сообщение отвечено
    await callback_query.message.edit_reply_markup(reply_markup=None)


@dp.message(FeedbackStates.waiting_for_admin_reply)
async def process_admin_reply(message: Message, state: FSMContext):
    """Админ отправляет ответ пользователю"""
    
    # Проверяем, что это админ
    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет прав для этого действия.")
        await state.clear()
        return
    
    # Получаем ID пользователя из состояния
    data = await state.get_data()
    user_id = data.get("reply_to_user_id")
    
    if not user_id:
        await message.answer("Ошибка: не указан пользователь для ответа")
        await state.clear()
        return
    
    reply_text = message.text
    
    try:
        # Отправляем ответ пользователю
        await bot.send_message(
            chat_id=user_id,
            text=f"✉️ <b>Ответ администратора:</b>\n\n{reply_text}",
            parse_mode="HTML"
        )
        
        # Подтверждение админу
        await message.answer(f"✅ Ответ отправлен пользователю {user_id}")
        logger.info(f"Admin replied to user {user_id}")
        
    except Exception as e:
        logger.error(f"Error sending reply: {e}")
        await message.answer(
            f"❌ Не удалось отправить ответ. Возможно, пользователь заблокировал бота."
        )
    
    await state.clear()


@dp.message(lambda message: message.text == "/cancel")
async def cancel(message: Message, state: FSMContext):
    """Отмена текущего действия"""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нет активного действия для отмены")
        return
    
    await state.clear()
    await message.answer("Действие отменено")


@dp.message()
async def unknown(message: Message):
    """Все остальные сообщения"""
    await message.answer("Нажмите /start для начала работы")