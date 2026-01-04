"""
Кешування відповідей для швидшого доступу
"""
import hashlib
import json
import re
from typing import Optional, Dict
from datetime import datetime, timedelta


class ResponseCache:
    """Кешування відповідей для швидшого доступу"""
    
    def __init__(self, max_size: int = 200, ttl_hours: int = 24):
        self.cache: Dict[str, Dict] = {}
        self.max_size = max_size
        self.ttl = timedelta(hours=ttl_hours)
    
    def _get_cache_key(self, query: str, context_hash: str) -> str:
        """Генерація ключа кешу"""
        normalized_query = self._normalize_query(query)
        return hashlib.md5(
            f"{normalized_query}:{context_hash}".encode('utf-8')
        ).hexdigest()
    
    def _normalize_query(self, query: str) -> str:
        """Нормалізація запиту для кешу"""
        if not query:
            return ""
        
        # Приводимо до нижнього регістру
        normalized = query.lower().strip()
        
        # Видаляємо зайві пробіли
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Видаляємо пунктуацію (крім питальних знаків)
        normalized = re.sub(r'[^\w\s?]', '', normalized)
        
        # Сортуємо слова для однакових питань з різним порядком
        words = normalized.split()
        return ' '.join(sorted(set(words)))  # Видаляємо дублікати
    
    def get(self, query: str, context: Dict) -> Optional[str]:
        """Отримання з кешу"""
        if not query or not context:
            return None
        
        try:
            context_hash = hashlib.md5(
                json.dumps(context, sort_keys=True, ensure_ascii=False).encode('utf-8')
            ).hexdigest()
        except (TypeError, ValueError):
            # Якщо не вдалося серіалізувати контекст, не використовуємо кеш
            return None
        
        key = self._get_cache_key(query, context_hash)
        
        if key in self.cache:
            entry = self.cache[key]
            
            # Перевіряємо TTL
            if datetime.now() - entry["timestamp"] < self.ttl:
                return entry["response"]
            else:
                # Видаляємо застарілий запис
                del self.cache[key]
        
        return None
    
    def set(self, query: str, context: Dict, response: str):
        """Збереження в кеш"""
        if not query or not response:
            return
        
        # Якщо кеш переповнений - видаляємо найстаріший
        if len(self.cache) >= self.max_size:
            oldest_key = min(
                self.cache.keys(),
                key=lambda k: self.cache[k]["timestamp"]
            )
            del self.cache[oldest_key]
        
        try:
            context_hash = hashlib.md5(
                json.dumps(context, sort_keys=True, ensure_ascii=False).encode('utf-8')
            ).hexdigest()
        except (TypeError, ValueError):
            # Якщо не вдалося серіалізувати контекст, не зберігаємо в кеш
            return
        
        key = self._get_cache_key(query, context_hash)
        
        self.cache[key] = {
            "response": response,
            "timestamp": datetime.now(),
            "query": query
        }
    
    def clear(self):
        """Очищення кешу"""
        self.cache.clear()
    
    def get_stats(self) -> Dict:
        """Статистика кешу"""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "usage_percent": (len(self.cache) / self.max_size) * 100 if self.max_size > 0 else 0
        }

