"""
Обробники нагадувань
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import db
from keyboards import get_main_menu, get_back_keyboard, get_reminders_management_keyboard
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

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
        await message.answer("⬅️ Повертаємось до головного меню 👇", reply_markup=get_main_menu(user_id=message.from_user.id))
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
        await message.answer("⬅️ Повертаємось до головного меню 👇", reply_markup=get_main_menu(user_id=message.from_user.id))
        return
    
    try:
        date_str = message.text.strip()
        deadline_date = datetime.strptime(date_str, "%d.%m.%Y").date()
        
        # Перевірка, чи дата не в минулому
        if deadline_date < datetime.now().date():
            await message.answer(
                "❌ Дата не може бути в минулому! Введи майбутню дату у форматі ДД.ММ.РРРР 📅:",
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
            reply_markup=get_main_menu(user_id=message.from_user.id),
            parse_mode="HTML"
        )
        await state.clear()
    except ValueError:
        await message.answer(
            "❌ Невірний формат дати! Введи дату у форматі <b>ДД.ММ.РРРР</b> (наприклад: 15.07.2024) 📅:",
            reply_markup=get_back_keyboard(),
            parse_mode="HTML"
        )


@router.message(F.text.in_(["📋 Список", "📋 Мої нагадування"]))
async def list_reminders_handler(message: Message):
    """Список нагадувань з кнопками видалення"""
    reminders = await db.get_user_reminders(message.from_user.id)
    
    if not reminders:
        await message.answer(
            "⏰ <b>Мої нагадування</b>\n\n"
            "📭 У тебе поки немає активних нагадувань.\n\n"
            "💡 <i>Порада:</i> Створи нове нагадування через кнопку '➕ Створити нагадування'!",
            reply_markup=get_reminders_management_keyboard(),
            parse_mode="HTML"
        )
        return
    
    text = "📋 <b>Мої нагадування:</b>\n\n"
    keyboard_buttons = []
    
    for reminder in reminders:
        reminder_id = reminder['id']
        deadline_date = reminder['deadline_date']
        deadline_name = reminder['deadline_name']
        is_sent = "✅" if reminder['is_sent'] else "⏳"
        days_left = (deadline_date - datetime.now().date()).days
        
        text += f"{is_sent} <b>{deadline_name}</b>\n"
        text += f"   📅 {deadline_date.strftime('%d.%m.%Y')} ({days_left} днів)\n\n"
        
        # Додаємо кнопку видалення для кожного нагадування
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"🗑️ Видалити: {deadline_name[:30]}",
                callback_data=f"reminder_delete_{reminder_id}"
            )
        ])
    
    # Додаємо кнопку видалення всіх нагадувань
    if len(reminders) > 1:
        keyboard_buttons.append([
            InlineKeyboardButton(
                text="🗑️ Видалити всі нагадування",
                callback_data="reminder_delete_all"
            )
        ])
    
    keyboard_buttons.append([
        InlineKeyboardButton(
            text="⬅️ Назад до меню",
            callback_data="reminder_back_to_menu"
        )
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await message.answer(
        text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )


# Спочатку обробляємо специфічні callback (reminder_delete_all)
@router.callback_query(F.data == "reminder_delete_all")
async def delete_all_reminders_handler(callback: CallbackQuery):
    """Підтвердження видалення всіх нагадувань"""
    logger.info(f"Обробка видалення всіх нагадувань для user_id={callback.from_user.id}, callback_data={callback.data}")
    
    user_id = callback.from_user.id
    
    # Відповідаємо на callback одразу, щоб уникнути таймауту
    await callback.answer()
    
    # Перевіряємо, чи є нагадування
    reminders = await db.get_user_reminders(user_id)
    if not reminders:
        await callback.answer("❌ У вас немає нагадувань для видалення", show_alert=True)
        return
    
    # Показуємо підтвердження
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Так, видалити всі",
                callback_data="reminder_confirm_delete_all"
            ),
            InlineKeyboardButton(
                text="❌ Скасувати",
                callback_data="reminder_cancel_delete"
            )
        ]
    ])
    
    try:
        await callback.message.edit_text(
            f"⚠️ <b>Видалення всіх нагадувань</b>\n\n"
            f"Ви впевнені, що хочете видалити <b>всі {len(reminders)} нагадування</b>?\n\n"
            f"Цю дію неможливо скасувати!",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Помилка редагування повідомлення: {e}")
        await callback.message.answer(
            f"⚠️ <b>Видалення всіх нагадувань</b>\n\n"
            f"Ви впевнені, що хочете видалити <b>всі {len(reminders)} нагадування</b>?\n\n"
            f"Цю дію неможливо скасувати!",
            reply_markup=keyboard,
            parse_mode="HTML"
        )


# Потім обробляємо видалення одного нагадування
@router.callback_query(F.data.startswith("reminder_delete_"))
async def delete_reminder_handler(callback: CallbackQuery):
    """Видалення одного нагадування"""
    # Перевіряємо, чи це не "reminder_delete_all" (на всяк випадок)
    if callback.data == "reminder_delete_all":
        logger.warning("delete_reminder_handler отримав reminder_delete_all - це не повинно статися")
        return
    
    try:
        # Витягуємо ID нагадування з callback_data (формат: reminder_delete_123)
        reminder_id_str = callback.data.replace("reminder_delete_", "")
        if not reminder_id_str or not reminder_id_str.isdigit():
            logger.error(f"Невірний формат callback_data: {callback.data}")
            await callback.answer("❌ Помилка: невірний формат запиту", show_alert=True)
            return
        
        reminder_id = int(reminder_id_str)
        user_id = callback.from_user.id
        
        logger.info(f"Спроба видалення нагадування: reminder_id={reminder_id}, user_id={user_id}, callback_data={callback.data}")
        
        # Видаляємо нагадування
        deleted = await db.delete_reminder(reminder_id, user_id)
        
        logger.info(f"Результат видалення: {deleted}")
        
        if deleted:
            # Відповідаємо на callback одразу
            await callback.answer("✅ Нагадування видалено")
            
            # Оновлюємо список нагадувань
            reminders = await db.get_user_reminders(user_id)
            
            try:
                if not reminders:
                    # Додаємо кнопки для навігації
                    keyboard_buttons = [
                        [
                            InlineKeyboardButton(
                                text="➕ Створити нагадування",
                                callback_data="reminder_create_new"
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text="⬅️ До меню нагадувань",
                                callback_data="reminder_back_to_list"
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text="🏠 Головне меню",
                                callback_data="reminder_back_to_menu"
                            )
                        ]
                    ]
                    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
                    
                    await callback.message.edit_text(
                        "✅ <b>Нагадування видалено!</b>\n\n"
                        "📭 У тебе поки немає активних нагадувань.\n\n"
                        "💡 <i>Порада:</i> Створи нове нагадування через кнопку нижче!",
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )
                else:
                    text = "✅ <b>Нагадування видалено!</b>\n\n"
                    text += "📋 <b>Мої нагадування:</b>\n\n"
                    keyboard_buttons = []
                    
                    for reminder in reminders:
                        reminder_id = reminder['id']
                        deadline_date = reminder['deadline_date']
                        deadline_name = reminder['deadline_name']
                        is_sent = "✅" if reminder['is_sent'] else "⏳"
                        days_left = (deadline_date - datetime.now().date()).days
                        
                        text += f"{is_sent} <b>{deadline_name}</b>\n"
                        text += f"   📅 {deadline_date.strftime('%d.%m.%Y')} ({days_left} днів)\n\n"
                        
                        keyboard_buttons.append([
                            InlineKeyboardButton(
                                text=f"🗑️ Видалити: {deadline_name[:30]}",
                                callback_data=f"reminder_delete_{reminder_id}"
                            )
                        ])
                    
                    if len(reminders) > 1:
                        keyboard_buttons.append([
                            InlineKeyboardButton(
                                text="🗑️ Видалити всі нагадування",
                                callback_data="reminder_delete_all"
                            )
                        ])
                    
                    keyboard_buttons.append([
                        InlineKeyboardButton(
                            text="⬅️ Назад до меню",
                            callback_data="reminder_back_to_menu"
                        )
                    ])
                    
                    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
                    
                    await callback.message.edit_text(
                        text,
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )
            except Exception as e:
                logger.error(f"Помилка оновлення повідомлення після видалення: {e}")
                # Якщо не вдалося відредагувати, відправляємо нове повідомлення
                # Додаємо кнопки для навігації
                keyboard_buttons = [
                    [
                        InlineKeyboardButton(
                            text="📋 Список нагадувань",
                            callback_data="reminder_back_to_list"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="🏠 Головне меню",
                            callback_data="reminder_back_to_menu"
                        )
                    ]
                ]
                keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
                
                await callback.message.answer(
                    "✅ <b>Нагадування видалено!</b>\n\n"
                    "🔄 Оновіть список нагадувань, щоб побачити зміни.",
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
        else:
            await callback.answer("❌ Нагадування не знайдено або вже видалено", show_alert=True)
    except (ValueError, Exception) as e:
        logger.error(f"Помилка видалення нагадування: {e}", exc_info=True)
        await callback.answer("❌ Помилка при видаленні нагадування", show_alert=True)


@router.callback_query(F.data == "reminder_confirm_delete_all")
async def confirm_delete_all_reminders_handler(callback: CallbackQuery):
    """Підтверджене видалення всіх нагадувань"""
    user_id = callback.from_user.id
    
    try:
        deleted = await db.delete_all_reminders(user_id)
        
        if deleted:
            # Додаємо кнопки для навігації
            keyboard_buttons = [
                [
                    InlineKeyboardButton(
                        text="➕ Створити нагадування",
                        callback_data="reminder_create_new"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="⬅️ До меню нагадувань",
                        callback_data="reminder_back_to_list"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🏠 Головне меню",
                        callback_data="reminder_back_to_menu"
                    )
                ]
            ]
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            
            await callback.message.edit_text(
                "✅ <b>Всі нагадування видалено!</b>\n\n"
                "📭 Тепер у вас немає активних нагадувань.\n\n"
                "💡 Можете створити нові нагадування через кнопку нижче!",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            await callback.answer("✅ Всі нагадування видалено")
        else:
            await callback.answer("❌ Помилка при видаленні нагадувань", show_alert=True)
    except Exception as e:
        logger.error(f"Помилка видалення всіх нагадувань: {e}", exc_info=True)
        await callback.answer("❌ Помилка при видаленні нагадувань", show_alert=True)


@router.callback_query(F.data == "reminder_cancel_delete")
async def cancel_delete_reminders_handler(callback: CallbackQuery):
    """Скасування видалення нагадувань"""
    # Повертаємось до списку нагадувань
    user_id = callback.from_user.id
    reminders = await db.get_user_reminders(user_id)
    
    if not reminders:
        await callback.message.edit_text(
            "⏰ <b>Мої нагадування</b>\n\n"
            "📭 У тебе поки немає активних нагадувань.\n\n"
            "💡 <i>Порада:</i> Створи нове нагадування через кнопку '➕ Створити нагадування'!",
            parse_mode="HTML"
        )
    else:
        text = "📋 <b>Мої нагадування:</b>\n\n"
        keyboard_buttons = []
        
        for reminder in reminders:
            reminder_id = reminder['id']
            deadline_date = reminder['deadline_date']
            deadline_name = reminder['deadline_name']
            is_sent = "✅" if reminder['is_sent'] else "⏳"
            days_left = (deadline_date - datetime.now().date()).days
            
            text += f"{is_sent} <b>{deadline_name}</b>\n"
            text += f"   📅 {deadline_date.strftime('%d.%m.%Y')} ({days_left} днів)\n\n"
            
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"🗑️ Видалити: {deadline_name[:30]}",
                    callback_data=f"reminder_delete_{reminder_id}"
                )
            ])
        
        if len(reminders) > 1:
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text="🗑️ Видалити всі нагадування",
                    callback_data="reminder_delete_all"
                )
            ])
        
        keyboard_buttons.append([
            InlineKeyboardButton(
                text="⬅️ Назад до меню",
                callback_data="reminder_back_to_menu"
            )
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    
    await callback.answer("❌ Видалення скасовано")


@router.callback_query(F.data == "reminder_back_to_list")
async def reminder_back_to_list_handler(callback: CallbackQuery):
    """Повернення до списку нагадувань"""
    user_id = callback.from_user.id
    reminders = await db.get_user_reminders(user_id)
    
    if not reminders:
        keyboard_buttons = [
            [
                InlineKeyboardButton(
                    text="➕ Створити нагадування",
                    callback_data="reminder_create_new"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏠 Головне меню",
                    callback_data="reminder_back_to_menu"
                )
            ]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(
            "⏰ <b>Мої нагадування</b>\n\n"
            "📭 У тебе поки немає активних нагадувань.\n\n"
            "💡 <i>Порада:</i> Створи нове нагадування через кнопку нижче!",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        text = "📋 <b>Мої нагадування:</b>\n\n"
        keyboard_buttons = []
        
        for reminder in reminders:
            reminder_id = reminder['id']
            deadline_date = reminder['deadline_date']
            deadline_name = reminder['deadline_name']
            is_sent = "✅" if reminder['is_sent'] else "⏳"
            days_left = (deadline_date - datetime.now().date()).days
            
            text += f"{is_sent} <b>{deadline_name}</b>\n"
            text += f"   📅 {deadline_date.strftime('%d.%m.%Y')} ({days_left} днів)\n\n"
            
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"🗑️ Видалити: {deadline_name[:30]}",
                    callback_data=f"reminder_delete_{reminder_id}"
                )
            ])
        
        if len(reminders) > 1:
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text="🗑️ Видалити всі нагадування",
                    callback_data="reminder_delete_all"
                )
            ])
        
        keyboard_buttons.append([
            InlineKeyboardButton(
                text="⬅️ Назад до меню",
                callback_data="reminder_back_to_menu"
            )
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    
    await callback.answer()


@router.callback_query(F.data == "reminder_create_new")
async def reminder_create_new_handler(callback: CallbackQuery, state: FSMContext):
    """Початок створення нового нагадування з callback"""
    await callback.message.edit_text(
        "📝 <b>Створення нагадування</b>\n\n"
        "Введи назву нагадування (наприклад: 'Подача документів'):",
        parse_mode="HTML"
    )
    await state.set_state(ReminderStates.waiting_for_name)
    await callback.answer()


@router.callback_query(F.data == "reminder_back_to_menu")
async def reminder_back_to_menu_handler(callback: CallbackQuery):
    """Повернення до головного меню з нагадувань"""
    from keyboards import get_main_menu
    
    await callback.message.edit_text(
        "⬅️ <b>Повертаємось до головного меню</b>\n\n"
        "💡 Використовуй кнопки меню для навігації 👇",
        parse_mode="HTML"
    )
    
    # Відправляємо нове повідомлення з головним меню
    await callback.message.answer(
        "🏠 <b>Головне меню</b>",
        reply_markup=get_main_menu(user_id=callback.from_user.id),
        parse_mode="HTML"
    )
    
    await callback.answer()



