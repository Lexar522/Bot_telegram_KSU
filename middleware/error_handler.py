"""
Middleware для обробки помилок
"""
from typing import Callable, Awaitable, Any
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
import logging

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseMiddleware):
    """Middleware для централізованої обробки помилок"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: dict[str, Any]
    ) -> Any:
        """
        Обробляє помилки в обробниках
        
        Args:
            handler: Обробник події
            event: Подія Telegram
            data: Дані події
            
        Returns:
            Результат обробки
        """
        try:
            return await handler(event, data)
        except Exception as e:
            # Отримуємо user_id безпечно
            user_id = None
            if hasattr(event, "from_user") and event.from_user:
                if hasattr(event.from_user, "id"):
                    user_id = event.from_user.id
                elif isinstance(event.from_user, dict):
                    user_id = event.from_user.get("id", None)
            
            logger.error(
                f"Помилка в обробнику: {e}",
                exc_info=True,
                extra={
                    "event_type": type(event).__name__,
                    "user_id": user_id
                }
            )
            
            # Спробуємо відправити повідомлення про помилку користувачу
            if hasattr(event, "message") and event.message:
                try:
                    await event.message.answer(
                        "Вибач, сталася помилка при обробці твого запиту. "
                        "Спробуй переформулювати питання або звернися до приймальної комісії ХДУ за телефоном +380 552 494375."
                    )
                except Exception as send_error:
                    logger.error(f"Не вдалося відправити повідомлення про помилку: {send_error}")
            
            # Пропускаємо помилку далі (не перериваємо роботу бота)
            return None

