"""
Валідатор відповідей від AI
Перевіряє відповіді на заборонені університети, орфографію та інші помилки
"""
import re
from typing import Tuple, List
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Результат валідації"""
    is_valid: bool
    error_message: str = ""
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class ResponseValidator:
    """Валідатор відповідей від AI"""
    
    # Заборонені університети (повний список)
    FORBIDDEN_UNIVERSITIES = [
        # Харківські
        "харківський національний університет", "хну", "харну",
        "харківський національний університет імені в.н.каразіна",
        "харківський національний університет імені каразіна",
        "харківському державному університеті імені в. н. каразіна",
        "каразіна",
        "каразінський",
        "каразинський",
        # Київські
        "київський національний університет", "кну", "кпі",
        "київський національний університет імені леся победимова",
        "національний університет імені леся победимова",
        # Львівські
        "львівський університет", "львівський національний університет",
        # Одеські
        "одеський університет", "одеський національний університет",
        # Інші українські
        "університет імені адама міцкевича", "білосток", "міцкевич",
        "український державний університет імені михайла грушевського",
        # ХНТУ та інші технічні
        "хнту", "хнту імені івана сікорського", "івана сікорського",
        "сікорського", "хнту імені сікорського",
        # Інші можливі варіанти
        "дніпровський", "запорізький", "сумський", "чернігівський",
        "полтавський", "вінницький", "тернопільський", "івано-франківський",
        "луцький", "ужгородський", "хмельницький", "черкаський",
        "кропивницький", "миколаївський", "мелітопольський"
    ]
    
    # Російські слова
    RUSSIAN_WORDS = [
        "ответ", "почему", "вот", "здравствуйте", "фінансы",
        "ответить", "сказать", "понять"
    ]
    
    # Англійські слова (крім технічних термінів)
    ENGLISH_WORDS = [
        "welcome", "hello", "hi", "xdu", "knu"
    ]
    
    # Технічні фрази, які не повинні бути в відповіді
    TECHNICAL_PHRASES = [
        "витрання до користувача", "пішіть за", "поповнітьтесь",
        "я розумію", "я спробую", "що саме потрібно",
        "я можу допомогти", "я готовий"
    ]
    
    # Неправильні відмінки
    WRONG_CASES = [
        "тисяців", "тисяць", "тисяцїв", "грнівн", "гривні"
    ]
    
    # Критичні помилки в документах
    DOCUMENT_ERRORS = [
        "квіткове", "квіткове свідоцтво", "підставка", "підставка про",
        "підтвердження наявності документів з попередньої школи",
        "середнього спеціального навчально-підготовчого закладу"
    ]
    
    def validate(self, response: str) -> ValidationResult:
        """
        Валідує відповідь на помилки
        
        Args:
            response: Відповідь для валідації
            
        Returns:
            ValidationResult: Результат валідації
        """
        errors = []
        response_lower = response.lower()
        
        # Перевірка на заборонені університети
        forbidden_found = self._check_forbidden_universities(response_lower)
        if forbidden_found:
            errors.append(f"Згадано заборонений університет: {forbidden_found}")
        
        # Перевірка на російські слова
        russian_found = self._check_russian_words(response_lower)
        if russian_found:
            errors.append(f"Виявлено російське слово: {russian_found}")
        
        # Перевірка на англійські слова
        english_found = self._check_english_words(response_lower)
        if english_found:
            errors.append(f"Виявлено англійське слово: {english_found}")
        
        # Перевірка на технічні фрази
        technical_found = self._check_technical_phrases(response_lower)
        if technical_found:
            errors.append(f"Виявлено технічну фразу: {technical_found}")
        
        # Перевірка на неправильні відмінки
        wrong_case_found = self._check_wrong_cases(response_lower)
        if wrong_case_found:
            errors.append(f"Неправильний відмінок: {wrong_case_found}")
        
        # Перевірка на критичні помилки в документах
        document_error_found = self._check_document_errors(response_lower)
        if document_error_found:
            errors.append(f"Критична помилка в документах: {document_error_found}")
        
        is_valid = len(errors) == 0
        error_message = "; ".join(errors) if errors else ""
        
        return ValidationResult(
            is_valid=is_valid,
            error_message=error_message,
            errors=errors
        )
    
    def _check_forbidden_universities(self, text: str) -> str:
        """Перевіряє на заборонені університети"""
        # Швидка перевірка за ключовими підрядками, щоб не пропустити варіанти
        substr_bans = ["харків", "каразін", "каразин"]
        for sub in substr_bans:
            if sub in text:
                return sub
        for uni in self.FORBIDDEN_UNIVERSITIES:
            if uni in text:
                return uni
        return ""
    
    def _check_russian_words(self, text: str) -> str:
        """Перевіряє на російські слова"""
        for word in self.RUSSIAN_WORDS:
            if word in text:
                return word
        return ""
    
    def _check_english_words(self, text: str) -> str:
        """Перевіряє на англійські слова"""
        for word in self.ENGLISH_WORDS:
            if word in text:
                return word
        return ""
    
    def _check_technical_phrases(self, text: str) -> str:
        """Перевіряє на технічні фрази"""
        for phrase in self.TECHNICAL_PHRASES:
            if phrase in text:
                return phrase
        return ""
    
    def _check_wrong_cases(self, text: str) -> str:
        """Перевіряє на неправильні відмінки"""
        for wrong in self.WRONG_CASES:
            if wrong in text:
                return wrong
        return ""
    
    def _check_document_errors(self, text: str) -> str:
        """Перевіряє на критичні помилки в документах"""
        for error in self.DOCUMENT_ERRORS:
            if error in text:
                return error
        return ""

