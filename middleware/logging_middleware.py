"""
Middleware для логування
"""
from typing import Callable, Awaitable, Any
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update, Message, CallbackQuery
import logging

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Middleware для логування повідомлень та подій"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any]
    ) -> Any:
        """
        Логує події перед обробкою
        
        Args:
            handler: Обробник події
            event: Подія Telegram
            data: Дані події
            
        Returns:
            Результат обробки
        """
        # Логуємо повідомлення від користувача
        if isinstance(event, Message):
            message = event
            user = message.from_user
            username = user.username if user.username else "без username"
            text = message.text if message.text else "[без тексту]"
            contact_info = ""
            
            if message.contact:
                contact_info = f" [КОНТАКТ: {message.contact.phone_number}]"
            
            logger.info(
                f"📨 Повідомлення від {user.id} (@{username}): {text[:100]}{contact_info}"
            )
        
        # Логуємо callback запити
        elif isinstance(event, CallbackQuery):
            callback = event
            user = callback.from_user
            username = user.username if user.username else "без username"
            data_text = callback.data if callback.data else "[без даних]"
            logger.info(
                f"🔘 Callback від {user.id} (@{username}): {data_text[:100]}"
            )
        
        # Викликаємо обробник
        try:
            result = await handler(event, data)
            return result
        except Exception as e:
            logger.error(f"❌ Помилка в handler: {e}", exc_info=True)
            raise



