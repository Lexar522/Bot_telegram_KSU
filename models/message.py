"""
Моделі даних для повідомлень
"""
from dataclasses import dataclass
from typing import Optional, List, Dict
from datetime import datetime


@dataclass
class UserMessage:
    """Модель повідомлення користувача"""
    user_id: int
    text: str
    message_id: Optional[int] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class MessageContext:
    """Контекст повідомлення (історія діалогу)"""
    user_id: int
    current_message: UserMessage
    history: List[Dict[str, str]] = None
    
    def __post_init__(self):
        if self.history is None:
            self.history = []
    
    def add_to_history(self, user_message: str, bot_response: str):
        """Додає повідомлення до історії"""
        self.history.append({
            "user_message": user_message,
            "bot_response": bot_response
        })
        
        # Обмежуємо історію останніми 5 повідомленнями
        if len(self.history) > 5:
            self.history = self.history[-5:]



