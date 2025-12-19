"""
Middleware для логування
"""
from typing import Callable, Awaitable, Any
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update, Message
import logging

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Middleware для логування повідомлень"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: dict[str, Any]
    ) -> Any:
        """
        Логує повідомлення перед обробкою
        
        Args:
            handler: Обробник події
            event: Подія Telegram
            data: Дані події
            
        Returns:
            Результат обробки
        """
        # Логуємо повідомлення від користувача
        if hasattr(event, "message") and event.message:
            message: Message = event.message
            user = message.from_user
            
            logger.info(
                f"Повідомлення від користувача {user.id} (@{user.username}): {message.text[:100]}"
            )
        
        # Викликаємо обробник
        result = await handler(event, data)
        
        return result



