"""
Валідатор контенту відповідей
Перевіряє структуру, формат та коректність відповіді
"""
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class ContentValidationResult:
    """Результат валідації контенту"""
    is_valid: bool
    issues: List[str] = None
    suggestions: List[str] = None
    
    def __post_init__(self):
        if self.issues is None:
            self.issues = []
        if self.suggestions is None:
            self.suggestions = []


class ContentValidator:
    """Валідатор контенту відповідей"""
    
    MIN_LENGTH = 10  # Мінімальна довжина відповіді
    MAX_LENGTH = 3500  # Максимальна довжина відповіді
    
    def validate(self, response: str) -> ContentValidationResult:
        """
        Валідує контент відповіді
        
        Args:
            response: Відповідь для валідації
            
        Returns:
            ContentValidationResult: Результат валідації
        """
        issues = []
        suggestions = []
        
        # Перевірка довжини
        if len(response) < self.MIN_LENGTH:
            issues.append(f"Відповідь занадто коротка ({len(response)} символів)")
            suggestions.append("Додай більше інформації")
        
        if len(response) > self.MAX_LENGTH:
            issues.append(f"Відповідь занадто довга ({len(response)} символів)")
            suggestions.append("Скороти відповідь до 3500 символів")
        
        # Перевірка на порожню відповідь
        if not response.strip():
            issues.append("Відповідь порожня")
            suggestions.append("Сформуй відповідь на питання")
        
        # Перевірка на зайві пробіли
        if response != response.strip():
            issues.append("Відповідь містить зайві пробіли на початку/в кінці")
            suggestions.append("Видали зайві пробіли")
        
        is_valid = len(issues) == 0
        
        return ContentValidationResult(
            is_valid=is_valid,
            issues=issues,
            suggestions=suggestions
        )



