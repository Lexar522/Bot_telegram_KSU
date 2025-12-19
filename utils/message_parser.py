"""
Утиліта для парсингу повідомлень користувача
"""
import re
from typing import Optional, Tuple


class MessageParser:
    """Утиліта для парсингу повідомлень"""
    
    @staticmethod
    def is_tuition_question(message: str) -> bool:
        """
        Перевіряє, чи це питання про вартість навчання
        
        Args:
            message: Повідомлення користувача
            
        Returns:
            bool: True якщо це питання про вартість
        """
        message_lower = message.lower()
        
        # Ключові слова про вартість
        tuition_keywords = [
            'вартість', 'ціна', 'скільки коштує', 'оплата', 
            'коштує навчання', 'тарифи', 'ціни'
        ]
        
        if any(keyword in message_lower for keyword in tuition_keywords):
            return True
        
        # Перевірка на коди спеціальностей (121, F6, A4.11 тощо)
        has_code = bool(re.search(
            r'\b(121|f6|f2|f3|код\s+\d{3}|код\s+[a-z]\d+|код\s+[a-z]\d+\.\d+|код\s+[а-я]\d+\.\d+)\b',
            message_lower,
            re.IGNORECASE
        ))
        
        return has_code
    
    @staticmethod
    def extract_specialty_code(message: str) -> Optional[str]:
        """
        Витягує код спеціальності з повідомлення
        
        Args:
            message: Повідомлення користувача
            
        Returns:
            Optional[str]: Код спеціальності або None
        """
        # Шукаємо 3-значні коди
        match = re.search(r'\b(\d{3})\b', message)
        if match:
            code = match.group(1)
            # Перевіряємо, чи це не рік
            if not code.startswith('20'):
                return code
        
        # Шукаємо коди з літерами (F6, F2, A4.11 тощо)
        match = re.search(r'\b([a-zа-я]\d+(?:\.\d+)?)\b', message, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        
        return None
    
    @staticmethod
    def get_question_type(message: str) -> str:
        """
        Визначає тип питання
        
        Args:
            message: Повідомлення користувача
            
        Returns:
            str: Тип питання (tuition, specialty, general, contact, documents)
        """
        message_lower = message.lower()
        
        if MessageParser.is_tuition_question(message):
            return 'tuition'
        
        if any(word in message_lower for word in [
            'спеціальності', 'спеціальність', 'факультети', 'факультет'
        ]):
            return 'specialty'
        
        if any(word in message_lower for word in [
            'контакти', 'телефон', 'адреса', 'зв\'язатися', 'звязатися'
        ]):
            return 'contact'
        
        if any(word in message_lower for word in [
            'документи', 'документ', 'потрібно', 'необхідно'
        ]):
            return 'documents'
        
        return 'general'



