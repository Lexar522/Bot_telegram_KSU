"""
Багаторівнева валідація відповідей
"""
from typing import List
from dataclasses import dataclass
from validators.response_validator import ResponseValidator, ValidationResult


@dataclass
class ValidationLevel:
    """Рівень валідації"""
    name: str
    weight: float
    validator: callable


class MultiLevelValidator:
    """Багаторівнева валідація відповідей"""
    
    def __init__(self):
        self.base_validator = ResponseValidator()
        
        # Рівні валідації
        self.levels = [
            ValidationLevel(
                name="quick",
                weight=1.0,
                validator=self._quick_validation
            ),
            ValidationLevel(
                name="detailed",
                weight=2.0,
                validator=self._detailed_validation
            ),
            ValidationLevel(
                name="semantic",
                weight=1.5,
                validator=self._semantic_validation
            )
        ]
    
    def validate(self, response: str, query: str) -> ValidationResult:
        """Багаторівнева валідація"""
        if not response:
            return ValidationResult(
                is_valid=False,
                error_message="Порожня відповідь",
                errors=["Порожня відповідь"]
            )
        
        all_errors = []
        total_weight = 0
        
        for level in self.levels:
            result = level.validator(response, query)
            if not result.is_valid:
                # Зважуємо помилки за важливістю рівня
                weighted_errors = [
                    f"[{level.name}] {error}" 
                    for error in (result.errors or [])
                ]
                all_errors.extend(weighted_errors)
                total_weight += level.weight
        
        is_valid = len(all_errors) == 0
        error_message = "; ".join(all_errors) if all_errors else ""
        
        return ValidationResult(
            is_valid=is_valid,
            error_message=error_message,
            errors=all_errors
        )
    
    def _quick_validation(self, response: str, query: str) -> ValidationResult:
        """Швидка перевірка критичних помилок"""
        response_lower = response.lower()
        
        # Перевірка на заборонені університети
        forbidden = self.base_validator._check_forbidden_universities(response_lower)
        if forbidden:
            return ValidationResult(
                is_valid=False,
                errors=[f"Заборонений університет: {forbidden}"]
            )
        
        # Перевірка на порожню відповідь
        if not response or len(response.strip()) < 10:
            return ValidationResult(
                is_valid=False,
                errors=["Порожня або занадто коротка відповідь"]
            )
        
        return ValidationResult(is_valid=True, errors=[])
    
    def _detailed_validation(self, response: str, query: str) -> ValidationResult:
        """Детальна перевірка"""
        return self.base_validator.validate(response)
    
    def _semantic_validation(self, response: str, query: str) -> ValidationResult:
        """Семантична перевірка релевантності"""
        if not query:
            return ValidationResult(is_valid=True, errors=[])
        
        query_lower = query.lower()
        response_lower = response.lower()
        
        # Витягуємо ключові слова з питання
        query_keywords = self._extract_keywords(query)
        
        if not query_keywords:
            return ValidationResult(is_valid=True, errors=[])
        
        # Перевіряємо наявність ключових слів у відповіді
        found_keywords = sum(
            1 for kw in query_keywords 
            if kw in response_lower
        )
        
        # Якщо менше 30% ключових слів знайдено - відповідь нерелевантна
        if found_keywords / len(query_keywords) < 0.3:
            return ValidationResult(
                is_valid=False,
                errors=["Відповідь не відповідає на питання"]
            )
        
        return ValidationResult(is_valid=True, errors=[])
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Витягування ключових слів"""
        import re
        stop_words = {"як", "що", "де", "коли", "чи", "для", "про", "на", "в", "з", "та", "і", "або"}
        words = re.findall(r'\b\w+\b', text.lower())
        return [w for w in words if w not in stop_words and len(w) > 2]

