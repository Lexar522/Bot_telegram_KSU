"""
Обробники callback queries
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery
from database import db
from knowledge_base import get_faculty_specialties
from keyboards import get_feedback_keyboard
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
        
        # Отримуємо спеціальності факультету
        specialties = get_faculty_specialties(faculty_id)
        
        if specialties:
            # Зберігаємо відповідь в історію
            message_history_id = await db.save_message_history(
                callback.from_user.id,
                f"Вибір факультету: {faculty_id}",
                specialties
            )
            
            # Відправляємо відповідь
            await callback.message.edit_text(
                specialties,
                reply_markup=get_feedback_keyboard(message_history_id) if message_history_id else None,
                parse_mode="HTML"
            )
            await callback.answer()
        else:
            await callback.answer("Факультет не знайдено", show_alert=True)
    except Exception as e:
        logger.error(f"Помилка обробки вибору факультету: {e}")
        await callback.answer("Помилка при обробці", show_alert=True)


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
            await callback.answer("Запис не знайдено", show_alert=True)
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
        await callback.answer("Помилка при збереженні звіту", show_alert=True)



