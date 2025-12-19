"""
Утиліта для форматування тексту
"""
import re
from typing import Optional


class TextFormatter:
    """Утиліта для форматування тексту"""
    
    def format(self, text: str) -> str:
        """
        Форматує текст для Telegram (markdown -> HTML)
        
        Args:
            text: Текст для форматування
            
        Returns:
            str: Відформатований текст
        """
        if not text:
            return text
        
        # Обробляємо маркери списку
        text = re.sub(r'^\s*\*\s+', '• ', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*-\s+', '• ', text, flags=re.MULTILINE)
        
        # Обробляємо жирний текст (**текст**)
        text = re.sub(r'\*\*([^*]+?)\*\*', r'<b>\1</b>', text)
        
        # Обробляємо курсив (*текст*)
        text = re.sub(r'(?<!\*)\*([^*\n\s][^*\n]*?[^*\n\s])\*(?!\*)', r'<i>\1</i>', text)
        
        # Видаляємо залишкові одинарні зірочки
        text = re.sub(r'(?<!\*)\*(?!\*)', '', text)
        
        # Очищаємо від зайвих пробілів
        text = text.strip()
        
        return text
    
    def remove_duplicates(self, text: str) -> str:
        """
        Видаляє дублікати рядків
        
        Args:
            text: Текст для обробки
            
        Returns:
            str: Текст без дублікатів
        """
        lines = text.split('\n')
        seen = set()
        unique_lines = []
        
        for line in lines:
            line_stripped = line.strip()
            if line_stripped and line_stripped not in seen:
                seen.add(line_stripped)
                unique_lines.append(line)
        
        return '\n'.join(unique_lines)
    
    def limit_length(self, text: str, max_length: int = 3500) -> str:
        """
        Обмежує довжину тексту
        
        Args:
            text: Текст для обробки
            max_length: Максимальна довжина
            
        Returns:
            str: Обрізаний текст
        """
        if len(text) <= max_length:
            return text
        
        return text[:max_length] + "\n\n... (повідомлення обрізано)"



