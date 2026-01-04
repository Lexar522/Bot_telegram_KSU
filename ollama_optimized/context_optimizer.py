"""
Оптимізація контексту для зменшення використання токенів
"""
import re
import json
from typing import Dict, List


class ContextOptimizer:
    """Оптимізація контексту для зменшення використання токенів"""
    
    MAX_CONTEXT_TOKENS = 2000  # Максимальна кількість символів в контексті (приблизно 500 токенів)
    
    # Пріоритети секцій
    SECTION_PRIORITY = {
        "high": ["university", "contacts", "admission", "documents"],
        "medium": ["faculties", "tuition", "fields"],
        "low": ["achievements", "international"]
    }
    
    def optimize_context(self, query: str, full_knowledge: Dict) -> Dict:
        """Оптимізація контексту на основі запиту"""
        # 1. Визначаємо ключові слова
        keywords = self._extract_keywords(query)
        
        # 2. Знаходимо релевантні секції
        relevant_sections = self._find_relevant_sections(keywords, full_knowledge)
        
        # 3. Пріоритизуємо секції
        prioritized = self._prioritize_sections(relevant_sections, full_knowledge)
        
        # 4. Обмежуємо розмір
        optimized = self._limit_context_size(prioritized)
        
        # 5. Завжди додаємо важливі секції
        if "university" in full_knowledge:
            optimized["university"] = full_knowledge["university"]
        if "contacts" in full_knowledge:
            optimized["contacts"] = full_knowledge["contacts"]
        
        return optimized
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Витягування ключових слів з запиту"""
        if not query:
            return []
        
        # Видаляємо стоп-слова
        stop_words = {"як", "що", "де", "коли", "чи", "для", "про", "на", "в", "з", "та", "і", "або"}
        
        words = re.findall(r'\b\w+\b', query.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        return keywords
    
    def _find_relevant_sections(self, keywords: List[str], knowledge: Dict) -> Dict:
        """Пошук релевантних секцій"""
        relevant = {}
        
        if not keywords:
            return relevant
        
        for section_key, section_data in knowledge.items():
            if section_data is None:
                continue
            
            section_str = str(section_data).lower()
            
            # Рахуємо збіги ключових слів
            matches = sum(1 for kw in keywords if kw in section_str)
            
            if matches > 0:
                relevant[section_key] = {
                    "data": section_data,
                    "relevance_score": matches / len(keywords) if keywords else 0
                }
        
        return relevant
    
    def _prioritize_sections(self, sections: Dict, full_knowledge: Dict) -> Dict:
        """Пріоритизація секцій"""
        prioritized = {}
        
        # Спочатку додаємо секції з високим пріоритетом
        for priority_level in ["high", "medium", "low"]:
            for section_key in self.SECTION_PRIORITY[priority_level]:
                if section_key in full_knowledge:
                    prioritized[section_key] = full_knowledge[section_key]
                elif section_key in sections:
                    prioritized[section_key] = sections[section_key]["data"]
        
        # Потім додаємо інші релевантні секції
        for section_key, section_info in sections.items():
            if section_key not in prioritized:
                prioritized[section_key] = section_info["data"]
        
        return prioritized
    
    def _limit_context_size(self, context: Dict) -> Dict:
        """Обмеження розміру контексту"""
        # Перевіряємо розмір
        try:
            context_str = json.dumps(context, ensure_ascii=False)
        except (TypeError, ValueError):
            context_str = str(context)
        
        estimated_chars = len(context_str)
        
        if estimated_chars <= self.MAX_CONTEXT_TOKENS:
            return context
        
        # Якщо занадто великий - обрізаємо низькопріоритетні секції
        limited = {}
        current_chars = 0
        
        for priority_level in ["high", "medium", "low"]:
            for section_key in self.SECTION_PRIORITY[priority_level]:
                if section_key in context:
                    try:
                        section_str = json.dumps(context[section_key], ensure_ascii=False)
                    except (TypeError, ValueError):
                        section_str = str(context[section_key])
                    
                    section_chars = len(section_str)
                    
                    if current_chars + section_chars <= self.MAX_CONTEXT_TOKENS:
                        limited[section_key] = context[section_key]
                        current_chars += section_chars
                    else:
                        # Частково додаємо секцію, якщо можна
                        if current_chars < self.MAX_CONTEXT_TOKENS * 0.8:  # Залишаємо 20% запасу
                            limited[section_key] = context[section_key]
                        break
        
        return limited

