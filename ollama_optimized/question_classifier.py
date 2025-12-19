"""
Класифікація питань для вибору оптимальної стратегії генерації
"""
import re
from typing import Dict


class QuestionClassifier:
    """Класифікація питань для вибору оптимальної стратегії"""
    
    QUESTION_PATTERNS = {
        "factual": [
            r"які\s+є", r"що\s+таке", r"де\s+знаходиться",
            r"скільки\s+є", r"які\s+спеціальності", r"які\s+факультети"
        ],
        "comparison": [
            r"порівняй", r"в\s+чому\s+різниця", r"що\s+краще",
            r"яка\s+різниця", r"скільки\s+різних", r"як\s+відрізняються"
        ],
        "procedural": [
            r"як\s+подати", r"які\s+кроки", r"що\s+потрібно\s+зробити",
            r"як\s+вступити", r"як\s+підготуватися", r"як\s+оформити"
        ],
        "admission": [
            r"вступ", r"нмт", r"документ", r"кампанія",
            r"правила\s+вступу", r"правила\s+прийому", r"порядок\s+вступу",
            r"траєкторії", r"електронний\s+кабінет",
            r"ksu24", r"ксу24", r"вступна\s+кампанія", r"правила"
        ],
        "tuition": [
            r"вартість", r"ціна", r"скільки\s+коштує",
            r"оплата", r"тарифи", r"коштує\s+навчання"
        ],
        "faculties": [
            r"факультет", r"спеціальність", r"напрям",
            r"освітні\s+програми", r"які\s+є\s+факультети"
        ]
    }
    
    def classify(self, query: str) -> str:
        """Класифікація питання"""
        if not query:
            return "factual"
        
        query_lower = query.lower()
        
        # Перевіряємо специфічні типи (в порядку пріоритету)
        # Спочатку перевіряємо більш специфічні типи
        priority_order = ["admission", "tuition", "faculties", "comparison", "procedural", "factual"]
        
        for q_type in priority_order:
            if q_type == "factual":
                continue  # Це за замовчуванням
            patterns = self.QUESTION_PATTERNS.get(q_type, [])
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return q_type
        
        # За замовчуванням - фактичне питання
        return "factual"
    
    def get_confidence(self, query: str, question_type: str) -> float:
        """Оцінка впевненості в класифікації"""
        if not query:
            return 0.0
        
        query_lower = query.lower()
        patterns = self.QUESTION_PATTERNS.get(question_type, [])
        
        if not patterns:
            return 0.0
        
        matches = sum(1 for pattern in patterns if re.search(pattern, query_lower))
        return matches / len(patterns) if patterns else 0.0

