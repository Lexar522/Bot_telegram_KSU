"""
Модуль обробників для Telegram-бота
"""
from aiogram import Router
from .commands import router as commands_router
from .menu_handlers import router as menu_router
from .chat_handler import router as chat_router
from .reminders import router as reminders_router
from .settings import router as settings_router
from .callbacks import router as callbacks_router
from .admin_callbacks import router as admin_callbacks_router

# Створюємо головний router та об'єднуємо всі під-роутери
router = Router()

# Додаємо всі під-роутери
# ВАЖЛИВО: commands_router має бути ПЕРШИМ, щоб команди оброблялися до chat_handler
router.include_router(commands_router)
router.include_router(menu_router)
router.include_router(reminders_router)
router.include_router(settings_router)
router.include_router(callbacks_router)
router.include_router(admin_callbacks_router)
# chat_router має бути ОСТАННІМ, бо він обробляє всі повідомлення без фільтрів
router.include_router(chat_router)

__all__ = ['router']



