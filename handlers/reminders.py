"""
Обробники нагадувань
"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import db
from keyboards import get_main_menu, get_back_keyboard, get_reminders_management_keyboard
from datetime import datetime

router = Router()


# FSM стани для створення нагадувань
class ReminderStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_date = State()


@router.message(F.text.in_(["➕ Створити", "➕ Створити нагадування"]))
async def create_reminder_start(message: Message, state: FSMContext):
    """Початок створення нагадування"""
    await message.answer(
        "📝 <b>Створення нагадування</b>\n\n"
        "Введи назву нагадування (наприклад: 'Подача документів'):",
        reply_markup=get_back_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(ReminderStates.waiting_for_name)


@router.message(ReminderStates.waiting_for_name)
async def process_reminder_name(message: Message, state: FSMContext):
    """Обробка назви нагадування"""
    if message.text == "⬅️ Назад":
        await state.clear()
        await message.answer("Повертаємось до головного меню 👇", reply_markup=get_main_menu())
        return
    
    await state.update_data(name=message.text)
    await message.answer(
        "📅 Тепер введи дату у форматі <b>ДД.ММ.РРРР</b> (наприклад: 15.07.2024):",
        reply_markup=get_back_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(ReminderStates.waiting_for_date)


@router.message(ReminderStates.waiting_for_date)
async def process_reminder_date(message: Message, state: FSMContext):
    """Обробка дати нагадування"""
    if message.text == "⬅️ Назад":
        await state.clear()
        await message.answer("Повертаємось до головного меню 👇", reply_markup=get_main_menu())
        return
    
    try:
        date_str = message.text.strip()
        deadline_date = datetime.strptime(date_str, "%d.%m.%Y").date()
        
        # Перевірка, чи дата не в минулому
        if deadline_date < datetime.now().date():
            await message.answer(
                "❌ Дата не може бути в минулому! Введи майбутню дату у форматі ДД.ММ.РРРР:",
                reply_markup=get_back_keyboard()
            )
            return
        
        data = await state.get_data()
        reminder_name = data.get("name")
        
        await db.add_reminder(message.from_user.id, deadline_date, reminder_name)
        
        await message.answer(
            f"✅ <b>Нагадування створено!</b>\n\n"
            f"📝 Назва: {reminder_name}\n"
            f"📅 Дата: {deadline_date.strftime('%d.%m.%Y')}\n\n"
            f"Я нагадаю тобі за 7, 3 та 1 день до цієї дати! ⏰",
            reply_markup=get_main_menu(),
            parse_mode="HTML"
        )
        await state.clear()
    except ValueError:
        await message.answer(
            "❌ Невірний формат дати! Введи дату у форматі <b>ДД.ММ.РРРР</b> (наприклад: 15.07.2024):",
            reply_markup=get_back_keyboard(),
            parse_mode="HTML"
        )


@router.message(F.text.in_(["📋 Список", "📋 Мої нагадування"]))
async def list_reminders_handler(message: Message):
    """Список нагадувань"""
    reminders = await db.get_user_reminders(message.from_user.id)
    
    if not reminders:
        await message.answer(
            "⏰ У тебе поки немає активних нагадувань.\n\n"
            "Створи нове нагадування через кнопку '➕ Створити нагадування'!",
            reply_markup=get_reminders_management_keyboard()
        )
        return
    
    text = "📋 <b>Мої нагадування:</b>\n\n"
    for reminder in reminders:
        deadline_date = reminder['deadline_date']
        deadline_name = reminder['deadline_name']
        is_sent = "✅" if reminder['is_sent'] else "⏳"
        days_left = (deadline_date - datetime.now().date()).days
        text += f"{is_sent} <b>{deadline_name}</b>\n"
        text += f"   📅 {deadline_date.strftime('%d.%m.%Y')} ({days_left} днів)\n\n"
    
    await message.answer(text, reply_markup=get_reminders_management_keyboard(), parse_mode="HTML")



