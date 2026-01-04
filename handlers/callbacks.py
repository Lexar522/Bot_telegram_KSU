"""
Обробники callback queries
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import db
from knowledge_base import get_faculty_specialties, get_admissions_committee_phones
from keyboards import get_feedback_keyboard, get_admin_menu
from config import ADMIN_ID
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data.startswith("faculty_"))
async def faculty_handler(callback: CallbackQuery):
    """Обробка вибору факультету"""
    try:
        faculty_id = callback.data  # Наприклад, "faculty_1"
        
        # Отримуємо тільки заголовок факультету БЕЗ списку спеціальностей (бо є кнопки)
        from knowledge_base import get_faculty_header_only
        from keyboards import get_specialties_keyboard
        
        faculty_text = get_faculty_header_only(faculty_id)
        
        # Додаємо підказку про кнопки
        faculty_text += "\n\n💡 <b>Обери спеціальність, щоб побачити вартість навчання</b> 💰"
        
        if faculty_text:
            # Зберігаємо відповідь в історію
            message_history_id = await db.save_message_history(
                callback.from_user.id,
                f"Вибір факультету: {faculty_id}",
                faculty_text
            )
            
            # Створюємо клавіатуру з кнопками спеціальностей
            specialties_keyboard = get_specialties_keyboard(faculty_id, report_id=message_history_id)
            
            # Відправляємо відповідь з кнопками спеціальностей
            await callback.message.edit_text(
                faculty_text,
                reply_markup=specialties_keyboard,
                parse_mode="HTML"
            )
            await callback.answer()
        else:
            await callback.answer("❌ Факультет не знайдено", show_alert=True)
    except Exception as e:
        logger.error(f"Помилка обробки вибору факультету: {e}", exc_info=True)
        await callback.answer("❌ Помилка при обробці", show_alert=True)


@router.callback_query(F.data.startswith("specialty_"))
async def specialty_handler(callback: CallbackQuery):
    """Обробка вибору спеціальності - показ вартості навчання"""
    try:
        # Формат callback_data: specialty_{faculty_id}_{specialty_idx}
        parts = callback.data.split("_")
        if len(parts) < 3:
            await callback.answer("Некоректні дані", show_alert=True)
            return
        
        faculty_id = f"faculty_{parts[1]}"  # Наприклад, "faculty_1"
        specialty_idx = int(parts[2])
        
        # Отримуємо список спеціальностей факультету
        from knowledge_base import get_faculty_specialties_list, get_faculties_list
        from keyboards import get_specialties_keyboard, get_faculties_keyboard
        from tuition_helper import find_tuition_info
        
        specialties = get_faculty_specialties_list(faculty_id)
        
        if not specialties or specialty_idx >= len(specialties):
            await callback.answer("❌ Спеціальність не знайдено", show_alert=True)
            return
        
        specialty_name = specialties[specialty_idx]
        
        # Шукаємо вартість навчання для цієї спеціальності
        tuition_info = await find_tuition_info(specialty_name=specialty_name)
        
        # Формуємо відповідь
        if tuition_info and "немає даних" not in tuition_info.lower() and "не вказана" not in tuition_info.lower():
            # Якщо tuition_info вже містить заголовок, не додаємо його знову
            if tuition_info.startswith("Вартість навчання"):
                response_text = f"💰 {tuition_info}"
            else:
                response_text = f"💰 <b>Вартість навчання</b>\n\n<b>📚 {specialty_name}</b>\n\n{tuition_info}"
        else:
            response_text = (
                f"💰 <b>Вартість навчання</b>\n\n"
                f"📚 <b>{specialty_name}</b>\n\n"
                "ℹ️ Вартість навчання для цієї спеціальності поки не вказана.\n\n"
                f"Для отримання актуальної інформації звернися до приймальної комісії ХДУ:\n\n{get_admissions_committee_phones()}"
            )
        
        # Зберігаємо відповідь в історію
        message_history_id = await db.save_message_history(
            callback.from_user.id,
            f"Вибір спеціальності: {specialty_name}",
            response_text
        )
        
        # Створюємо клавіатуру з кнопкою "Назад до спеціальностей" та feedback
        # Використовуємо get_specialties_keyboard для кнопки "Назад", але додаємо feedback окремо
        from keyboards import get_feedback_keyboard
        
        buttons = [
            [
                InlineKeyboardButton(
                    text="⬅️ Назад до спеціальностей",
                    callback_data=faculty_id
                )
            ]
        ]
        
        # Додаємо кнопки feedback, якщо є message_history_id
        feedback_keyboard = get_feedback_keyboard(message_history_id) if message_history_id else None
        if feedback_keyboard and feedback_keyboard.inline_keyboard:
            buttons.extend(feedback_keyboard.inline_keyboard)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        # Відправляємо відповідь
        await callback.message.edit_text(
            response_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Помилка обробки вибору спеціальності: {e}", exc_info=True)
        await callback.answer("❌ Помилка при обробці", show_alert=True)


@router.callback_query(F.data == "back_to_faculties")
async def back_to_faculties_handler(callback: CallbackQuery):
    """Повернення до списку факультетів"""
    try:
        from keyboards import get_faculties_keyboard
        
        # Показуємо тільки заголовок та підказку (без списку, бо є кнопки)
        faculties_text = "📚 <b>Факультети ХДУ</b>\n\n💡 <b>Обери факультет, щоб побачити спеціальності та вартість навчання</b> 🎓"
        
        # Зберігаємо в історію
        message_history_id = await db.save_message_history(
            callback.from_user.id,
            "Перегляд факультетів",
            faculties_text
        )
        
        # Відправляємо відповідь з клавіатурою факультетів
        await callback.message.edit_text(
            faculties_text,
            reply_markup=get_faculties_keyboard(report_id=message_history_id),
            parse_mode="HTML"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Помилка повернення до факультетів: {e}", exc_info=True)
        await callback.answer("❌ Помилка при обробці", show_alert=True)


@router.callback_query(F.data.startswith("report_"))
async def report_error_handler(callback: CallbackQuery):
    """Обробка кнопки 'Повідомити про помилку'"""
    data = callback.data
    parts = data.split("_")
    if len(parts) < 2:
        await callback.answer("Некоректні дані", show_alert=True)
        return
    message_history_id = int(parts[1])
    
    try:
        # Отримуємо запис історії
        history_row = await db.get_message_history_by_id(message_history_id)
        if not history_row:
            await callback.answer("❌ Запис не знайдено", show_alert=True)
            return
        
        user_id = history_row["user_id"]
        user_message = history_row["user_message"]
        bot_response = history_row["bot_response"]
        
        # Логуємо у файл reports/error_reports.log
        from pathlib import Path
        reports_dir = Path(__file__).parent.parent / "reports"
        reports_dir.mkdir(exist_ok=True)
        report_path = reports_dir / "error_reports.log"
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = (
            f"[{timestamp}] user_id={user_id}, history_id={message_history_id}\n"
            f"User: {user_message}\n"
            f"Bot: {bot_response}\n"
            f"---\n"
        )
        with open(report_path, "a", encoding="utf-8") as f:
            f.write(log_entry)
        
        # Фіксуємо у БД як feedback типу 'report' (для статистики)
        await db.save_feedback(callback.from_user.id, message_history_id, "report")
        
        await callback.answer("Дякую! Записав помилку 🚩", show_alert=False)
    except Exception as e:
        logger.error(f"Помилка збереження звіту: {e}")
        await callback.answer("❌ Помилка при збереженні звіту", show_alert=True)


@router.callback_query(F.data.startswith("mark_processed_"))
async def mark_contact_processed_handler(callback: CallbackQuery):
    """Обробка відмітки контакту як опрацьований"""
    if callback.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await callback.answer("❌ У вас немає доступу", show_alert=True)
        return
    
    try:
        contact_id = int(callback.data.split("_")[-1])
        await db.mark_contact_as_processed(contact_id)
        
        # Отримуємо інформацію про контакт для оновлення повідомлення
        contacts = await db.get_all_shared_contacts()
        contact = next((c for c in contacts if c.get('id') == contact_id), None)
        
        # Оновлюємо текст повідомлення
        original_text = callback.message.text
        if "\n\n✅ <b>Відмічено як опрацьований</b>" not in original_text:
            new_text = original_text + "\n\n✅ <b>Відмічено як опрацьований</b>"
        else:
            new_text = original_text
        
        # Оновлюємо кнопки - додаємо можливість відмітити як неопрацьований
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="↩️ Відмітити як неопрацьований",
                    callback_data=f"mark_unprocessed_{contact_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑️ Видалити контакт",
                    callback_data=f"confirm_delete_contact_{contact_id}"
                )
            ]
        ])
        
        await callback.message.edit_text(new_text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer("✅ Контакт відмічено як опрацьований")
    except Exception as e:
        logger.error(f"Помилка відмітки контакту: {e}", exc_info=True)
        await callback.answer("❌ Помилка при обробці", show_alert=True)


@router.callback_query(F.data == "unprocessed_contacts")
async def show_unprocessed_contacts_handler(callback: CallbackQuery):
    """Показ неопрацьованих контактів"""
    if callback.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await callback.answer("❌ У вас немає доступу", show_alert=True)
        return
    
    try:
        contacts = await db.get_all_shared_contacts(only_unprocessed=True)
        
        if not contacts:
            await callback.message.answer(
                "✅ <b>Немає неопрацьованих контактів</b>\n\n"
                "Всі контакти опрацьовані!",
                parse_mode="HTML"
            )
            await callback.answer()
            return
        
        text = f"📋 <b>Неопрацьовані контакти ({len(contacts)}):</b>\n\n"
        
        for i, contact in enumerate(contacts, 1):
            contact_id = contact['id']
            text += f"<b>{i}.</b> {contact['user_name']}\n"
            if contact.get('phone_number'):
                # Форматуємо номер для клікабельності через HTML посилання
                phone_raw = str(contact['phone_number']).replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
                # Додаємо + якщо його немає
                if not phone_raw.startswith('+'):
                    phone_raw = '+' + phone_raw
                text += f"   📞 <a href=\"tel:{phone_raw}\">{phone_raw}</a>\n"
            if contact.get('telegram_first_name') or contact.get('telegram_username'):
                text += "   👤 Telegram: "
                if contact.get('telegram_first_name'):
                    text += contact['telegram_first_name']
                if contact.get('telegram_username'):
                    text += f" (@{contact['telegram_username']})"
                text += "\n"
            text += f"   📅 {contact['created_at'].strftime('%d.%m.%Y %H:%M')}\n"
            
            # Додаємо кнопки для кожного контакту
            contact_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Відмітити як опрацьований",
                        callback_data=f"mark_processed_{contact_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🗑️ Видалити",
                        callback_data=f"confirm_delete_contact_{contact_id}"
                    )
                ]
            ])
            
            await callback.message.answer(text, reply_markup=contact_keyboard, parse_mode="HTML")
            text = ""
        
        if text:
            await callback.message.answer(text, parse_mode="HTML")
        
        await callback.answer()
    except Exception as e:
        logger.error(f"Помилка показу неопрацьованих контактів: {e}", exc_info=True)
        await callback.answer("❌ Помилка при завантаженні", show_alert=True)


@router.callback_query(F.data == "all_contacts")
async def show_all_contacts_handler(callback: CallbackQuery):
    """Показ всіх контактів"""
    if callback.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await callback.answer("❌ У вас немає доступу", show_alert=True)
        return
    
    try:
        contacts = await db.get_all_shared_contacts()
        
        if not contacts:
            await callback.message.answer(
                "📋 <b>Список контактів порожній</b>",
                parse_mode="HTML"
            )
            await callback.answer()
            return
        
        text = f"👥 <b>Всі контакти абітурієнтів ({len(contacts)}):</b>\n\n"
        
        for i, contact in enumerate(contacts, 1):
            contact_id = contact['id']
            status = "✅" if contact.get('is_processed') else "⏳"
            text += f"{status} <b>{i}.</b> {contact['user_name']}\n"
            if contact.get('phone_number'):
                # Форматуємо номер для клікабельності через HTML посилання
                phone_raw = str(contact['phone_number']).replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
                # Додаємо + якщо його немає
                if not phone_raw.startswith('+'):
                    phone_raw = '+' + phone_raw
                text += f"   📞 <a href=\"tel:{phone_raw}\">{phone_raw}</a>\n"
            if contact.get('telegram_first_name') or contact.get('telegram_username'):
                text += "   👤 Telegram: "
                if contact.get('telegram_first_name'):
                    text += contact['telegram_first_name']
                if contact.get('telegram_username'):
                    text += f" (@{contact['telegram_username']})"
                text += "\n"
            text += f"   📅 {contact['created_at'].strftime('%d.%m.%Y %H:%M')}\n"
            
            # Додаємо кнопки для кожного контакту
            contact_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Відмітити як опрацьований" if not contact.get('is_processed') else "↩️ Відмітити як неопрацьований",
                        callback_data=f"mark_processed_{contact_id}" if not contact.get('is_processed') else f"mark_unprocessed_{contact_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🗑️ Видалити",
                        callback_data=f"confirm_delete_contact_{contact_id}"
                    )
                ]
            ])
            
            await callback.message.answer(text, reply_markup=contact_keyboard, parse_mode="HTML")
            text = ""
        
        if text:
            await callback.message.answer(text, parse_mode="HTML")
        
        await callback.answer()
    except Exception as e:
        logger.error(f"Помилка показу всіх контактів: {e}", exc_info=True)
        await callback.answer("❌ Помилка при завантаженні", show_alert=True)


@router.callback_query(F.data == "toggle_notifications")
async def toggle_notifications_handler(callback: CallbackQuery):
    """Увімкнути/вимкнути сповіщення про нові контакти"""
    if callback.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await callback.answer("❌ У вас немає доступу", show_alert=True)
        return
    
    try:
        current_setting = await db.get_admin_notifications_setting(ADMIN_ID)
        new_setting = not current_setting
        await db.set_admin_notifications(ADMIN_ID, new_setting)
        
        unprocessed_count = await db.get_unprocessed_contacts_count()
        status_text = "увімкнено ✅" if new_setting else "вимкнено ❌"
        
        await callback.message.edit_text(
            f"⚙️ <b>Налаштування сповіщень</b>\n\n"
            f"<b>Про що:</b> Сповіщення про нові запити абітурієнтів на зателефонувати\n\n"
            f"<b>Поточний стан:</b> сповіщення <b>{status_text}</b>\n\n"
            f"📊 <b>Неопрацьованих запитів:</b> {unprocessed_count}\n\n"
            f"{'✅ Ви будете отримувати повідомлення про нові контакти' if new_setting else '❌ Ви НЕ будете отримувати повідомлення про нові контакти'}.\n\n"
            f"Повідомлення приходять коли абітурієнт ділиться своїм контактом через бота.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="❌ Вимкнути сповіщення" if new_setting else "✅ Увімкнути сповіщення",
                        callback_data="toggle_notifications"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📊 Статистика контактів",
                        callback_data="contacts_stats"
                    )
                ]
            ]),
            parse_mode="HTML"
        )
        await callback.answer(f"Сповіщення {status_text}")
    except Exception as e:
        logger.error(f"Помилка зміни налаштувань сповіщень: {e}", exc_info=True)
        await callback.answer("❌ Помилка при зміні налаштувань", show_alert=True)


@router.callback_query(F.data == "contacts_stats")
async def contacts_stats_handler(callback: CallbackQuery):
    """Статистика контактів"""
    if callback.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await callback.answer("❌ У вас немає доступу", show_alert=True)
        return
    
    try:
        all_contacts = await db.get_all_shared_contacts()
        unprocessed_count = await db.get_unprocessed_contacts_count()
        processed_count = len(all_contacts) - unprocessed_count
        
        text = (
            f"📊 <b>Статистика контактів</b>\n\n"
            f"• Всього контактів: {len(all_contacts)}\n"
            f"• Неопрацьованих: {unprocessed_count}\n"
            f"• Опрацьованих: {processed_count}\n"
        )
        
        await callback.message.answer(text, parse_mode="HTML")
        await callback.answer()
    except Exception as e:
        logger.error(f"Помилка отримання статистики: {e}", exc_info=True)
        await callback.answer("❌ Помилка при завантаженні", show_alert=True)


@router.callback_query(F.data == "confirm_delete_processed")
async def confirm_delete_processed_handler(callback: CallbackQuery):
    """Підтвердження видалення опрацьованих контактів"""
    if callback.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await callback.answer("❌ У вас немає доступу", show_alert=True)
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Так, видалити", callback_data="delete_processed_yes"),
            InlineKeyboardButton(text="❌ Скасувати", callback_data="delete_cancel")
        ]
    ])
    
    await callback.message.edit_text(
        "⚠️ <b>Підтвердження видалення</b>\n\n"
        "Ви впевнені, що хочете видалити всі <b>опрацьовані</b> контакти?",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_delete_all")
async def confirm_delete_all_handler(callback: CallbackQuery):
    """Підтвердження видалення всіх контактів"""
    if callback.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await callback.answer("❌ У вас немає доступу", show_alert=True)
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Так, видалити все", callback_data="delete_all_yes"),
            InlineKeyboardButton(text="❌ Скасувати", callback_data="delete_cancel")
        ]
    ])
    
    await callback.message.edit_text(
        "⚠️ <b>Підтвердження видалення</b>\n\n"
        "Ви впевнені, що хочете видалити <b>ВСІ</b> контакти?\n"
        "Цю дію неможливо скасувати!",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "delete_processed_yes")
async def delete_processed_yes_handler(callback: CallbackQuery):
    """Видалення опрацьованих контактів"""
    if callback.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await callback.answer("❌ У вас немає доступу", show_alert=True)
        return
    
    try:
        await db.delete_processed_contacts()
        await callback.message.edit_text("✅ Опрацьовані контакти видалено")
        await callback.answer("✅ Контакти видалено")
    except Exception as e:
        logger.error(f"Помилка видалення контактів: {e}", exc_info=True)
        await callback.answer("❌ Помилка при видаленні", show_alert=True)


@router.callback_query(F.data == "delete_all_yes")
async def delete_all_yes_handler(callback: CallbackQuery):
    """Видалення всіх контактів"""
    if callback.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await callback.answer("❌ У вас немає доступу", show_alert=True)
        return
    
    try:
        await db.delete_all_contacts()
        await callback.message.edit_text("✅ Всі контакти видалено")
        await callback.answer("✅ Контакти видалено")
    except Exception as e:
        logger.error(f"Помилка видалення контактів: {e}", exc_info=True)
        await callback.answer("❌ Помилка при видаленні", show_alert=True)


@router.callback_query(F.data == "delete_cancel")
async def delete_cancel_handler(callback: CallbackQuery):
    """Скасування видалення"""
    if callback.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await callback.answer("❌ У вас немає доступу", show_alert=True)
        return
    
    await callback.message.edit_text("❌ Видалення скасовано")
    await callback.answer("❌ Скасовано")


@router.callback_query(F.data.startswith("confirm_delete_contact_"))
async def confirm_delete_contact_handler(callback: CallbackQuery):
    """Підтвердження видалення окремого контакту"""
    if callback.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await callback.answer("❌ У вас немає доступу", show_alert=True)
        return
    
    try:
        contact_id = int(callback.data.split("_")[-1])
        
        # Отримуємо інформацію про контакт
        contacts = await db.get_all_shared_contacts()
        contact = next((c for c in contacts if c.get('id') == contact_id), None)
        
        if not contact:
            await callback.answer("❌ Контакт не знайдено", show_alert=True)
            return
        
        contact_name = contact.get('user_name', 'невідомо')
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Так, видалити", callback_data=f"delete_contact_yes_{contact_id}"),
                InlineKeyboardButton(text="❌ Скасувати", callback_data="delete_cancel")
            ]
        ])
        
        await callback.message.edit_text(
            f"⚠️ <b>Підтвердження видалення</b>\n\n"
            f"Ви впевнені, що хочете видалити контакт:\n"
            f"<b>{contact_name}</b>?\n\n"
            f"Цю дію неможливо скасувати!",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Помилка підтвердження видалення контакту: {e}", exc_info=True)
        await callback.answer("❌ Помилка при обробці", show_alert=True)


@router.callback_query(F.data.startswith("delete_contact_yes_"))
async def delete_contact_yes_handler(callback: CallbackQuery):
    """Видалення окремого контакту"""
    if callback.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await callback.answer("❌ У вас немає доступу", show_alert=True)
        return
    
    try:
        contact_id = int(callback.data.split("_")[-1])
        deleted = await db.delete_contact_by_id(contact_id)
        
        if deleted:
            await callback.message.edit_text("✅ Контакт видалено")
            await callback.answer("✅ Контакт видалено")
        else:
            await callback.answer("❌ Контакт не знайдено", show_alert=True)
    except Exception as e:
        logger.error(f"Помилка видалення контакту: {e}", exc_info=True)
        await callback.answer("❌ Помилка при видаленні", show_alert=True)


@router.callback_query(F.data.startswith("mark_unprocessed_"))
async def mark_contact_unprocessed_handler(callback: CallbackQuery):
    """Відмітити контакт як неопрацьований"""
    if callback.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await callback.answer("❌ У вас немає доступу", show_alert=True)
        return
    
    try:
        contact_id = int(callback.data.split("_")[-1])
        
        # Оновлюємо контакт
        await db.mark_contact_as_unprocessed(contact_id)
        
        # Оновлюємо текст повідомлення (видаляємо попередню відмітку)
        original_text = callback.message.text
        # Видаляємо попередні відмітки
        new_text = original_text.replace("\n\n✅ <b>Відмічено як опрацьований</b>", "")
        new_text = new_text.replace("\n\n↩️ <b>Відмічено як неопрацьований</b>", "")
        new_text = new_text + "\n\n↩️ <b>Відмічено як неопрацьований</b>"
        
        # Оновлюємо кнопки
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Відмітити як опрацьований",
                    callback_data=f"mark_processed_{contact_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑️ Видалити контакт",
                    callback_data=f"confirm_delete_contact_{contact_id}"
                )
            ]
        ])
        
        await callback.message.edit_text(new_text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer("↩️ Контакт відмічено як неопрацьований")
    except Exception as e:
        logger.error(f"Помилка відмітки контакту: {e}", exc_info=True)
        await callback.answer("❌ Помилка при обробці", show_alert=True)



