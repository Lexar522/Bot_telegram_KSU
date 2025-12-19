"""
Модуль для планування нагадувань
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, date
from database import db
from aiogram import Bot
from config import BOT_TOKEN

scheduler = AsyncIOScheduler()
bot = Bot(token=BOT_TOKEN)


async def check_and_send_reminders():
    """Перевірка та відправка нагадувань"""
    if not db.pool:
        return
        
    # Отримуємо всіх користувачів
    async with db.pool.acquire() as conn:
        users = await conn.fetch("SELECT telegram_id FROM users WHERE is_active = TRUE")
        
        for user in users:
            telegram_id = user['telegram_id']
            # Отримуємо нагадування напряму через conn
            reminders = await conn.fetch(
                "SELECT * FROM reminders WHERE user_id = $1 AND is_sent = FALSE ORDER BY deadline_date",
                telegram_id
            )
            
            today = date.today()
            
            for reminder in reminders:
                deadline_date = reminder['deadline_date']
                days_until = (deadline_date - today).days
                
                # Надсилаємо нагадування за 7, 3 та 1 день до дедлайну
                if days_until in [7, 3, 1]:
                    try:
                        message = (
                            f"⏰ <b>Нагадування про дедлайн вступу до ХДУ</b>\n\n"
                            f"📅 {reminder['deadline_name']}\n"
                            f"📆 Дата: {deadline_date}\n"
                            f"⏳ Залишилось днів: {days_until}\n\n"
                            f"💡 Не забудь підготувати все необхідне для вступу до Херсонського державного університету!"
                        )
                        
                        await bot.send_message(telegram_id, message, parse_mode="HTML")
                        
                        # Позначаємо як відправлене
                        await conn.execute(
                            "UPDATE reminders SET is_sent = TRUE WHERE id = $1",
                            reminder['id']
                        )
                    except Exception as e:
                        print(f"Помилка відправки нагадування: {e}")


def start_scheduler():
    """Запуск планувальника"""
    # Перевіряємо нагадування щодня о 9:00
    scheduler.add_job(
        check_and_send_reminders,
        CronTrigger(hour=9, minute=0),
        id='daily_reminders',
        replace_existing=True
    )
    scheduler.start()
    print("✅ Планувальник нагадувань запущено")


def stop_scheduler():
    """Зупинка планувальника"""
    scheduler.shutdown()

