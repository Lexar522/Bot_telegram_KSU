"""
Обробники налаштувань
"""
from aiogram import Router, F
from aiogram.types import Message
from database import db
from keyboards import (
    get_main_menu, get_settings_keyboard, get_specializations_keyboard,
    get_reminders_management_keyboard
)

router = Router()


@router.message(F.text == "⚙️ Налаштування")
async def settings_handler(message: Message):
    """Обробка налаштувань"""
    user = await db.get_user(message.from_user.id)
    specialization = user.get("specialization") if user else None
    
    text = "⚙️ <b>Налаштування</b>\n\n"
    if specialization:
        text += f"🎯 Твоя спеціалізація: {specialization}\n\n"
    else:
        text += "🎯 Спеціалізація не встановлена\n\n"
    
    text += "Оберіть опцію:"
    
    await message.answer(text, reply_markup=get_settings_keyboard(), parse_mode="HTML")


@router.message(F.text.in_(["🎯 Спеціалізація", "🎯 Змінити спеціалізацію"]))
async def change_specialization_handler(message: Message):
    """Обробка зміни спеціалізації"""
    await message.answer(
        "🎯 Оберіть свою спеціалізацію:",
        reply_markup=get_specializations_keyboard()
    )


@router.message(F.text.in_(["🔔 Нагадування", "🔔 Увімкнути/вимкнути нагадування"]))
async def toggle_reminders_handler(message: Message):
    """Обробка увімкнення/вимкнення нагадувань"""
    # Показуємо меню нагадувань
    await message.answer(
        "⏰ <b>Управління нагадуваннями</b>\n\n"
        "Тут ти можеш створити нові нагадування або переглянути існуючі.",
        reply_markup=get_reminders_management_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text.in_([
    "💻 IT", "💻 Інформаційні технології", "🏥 Медицина", "⚖️ Право",
    "💰 Економіка", "🎓 Педагогіка", "🔬 Природничі науки", 
    "📝 Інша", "📝 Інша спеціалізація"
]))
async def set_specialization_handler(message: Message):
    """Встановлення спеціалізації"""
    specialization_map = {
        "💻 IT": "Інформаційні технології",
        "💻 Інформаційні технології": "Інформаційні технології",
        "🏥 Медицина": "Медицина",
        "⚖️ Право": "Право",
        "💰 Економіка": "Економіка",
        "🎓 Педагогіка": "Педагогіка",
        "🔬 Природничі науки": "Природничі науки",
        "📝 Інша": "Інша",
        "📝 Інша спеціалізація": "Інша"
    }
    
    specialization = specialization_map.get(message.text, message.text)
    await db.update_specialization(message.from_user.id, specialization)
    
    await message.answer(
        f"✅ Спеціалізацію встановлено: {specialization}\n\n"
        "Тепер ти отримуватимеш більш персоналізовані поради!",
        reply_markup=get_main_menu()
    )



