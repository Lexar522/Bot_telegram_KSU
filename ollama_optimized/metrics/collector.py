"""
Збір метрик для аналізу роботи AI
"""
from typing import Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Збір метрик для аналізу роботи AI"""
    
    def __init__(self):
        self.metrics = {
            "total_requests": 0,
            "cache_hits": 0,
            "validation_failures": 0,
            "regeneration_count": 0,
            "response_times": [],
            "response_lengths": [],
            "question_types": {},
            "errors_by_type": {}
        }
        # Обмежуємо розмір списків для пам'яті
        self.max_list_size = 1000
    
    def record_request(
        self, 
        query: str, 
        response: str, 
        response_time: float, 
        from_cache: bool,
        question_type: str = None,
        validation_passed: bool = True
    ):
        """Запис метрик запиту"""
        self.metrics["total_requests"] += 1
        
        if from_cache:
            self.metrics["cache_hits"] += 1
        
        if not validation_passed:
            self.metrics["validation_failures"] += 1
        
        if question_type:
            self.metrics["question_types"][question_type] = \
                self.metrics["question_types"].get(question_type, 0) + 1
        
        # Додаємо до списків (з обмеженням розміру)
        if len(self.metrics["response_times"]) < self.max_list_size:
            self.metrics["response_times"].append(response_time)
        else:
            # Видаляємо найстаріший і додаємо новий
            self.metrics["response_times"].pop(0)
            self.metrics["response_times"].append(response_time)
        
        if len(self.metrics["response_lengths"]) < self.max_list_size:
            self.metrics["response_lengths"].append(len(response))
        else:
            self.metrics["response_lengths"].pop(0)
            self.metrics["response_lengths"].append(len(response))
        
        # Зберігаємо в БД для аналізу (асинхронно, не блокуємо)
        try:
            # Викликаємо асинхронно через create_task
            import asyncio
            asyncio.create_task(self._save_to_db(query, response, response_time, from_cache, question_type))
        except Exception as e:
            logger.warning(f"Помилка збереження метрик: {e}")
    
    def get_statistics(self) -> Dict:
        """Отримання статистики"""
        total = self.metrics["total_requests"]
        
        if total == 0:
            return {}
        
        response_times = self.metrics["response_times"]
        response_lengths = self.metrics["response_lengths"]
        
        return {
            "total_requests": total,
            "cache_hit_rate": (self.metrics["cache_hits"] / total * 100) if total > 0 else 0,
            "validation_failure_rate": (self.metrics["validation_failures"] / total * 100) if total > 0 else 0,
            "avg_response_time": sum(response_times) / len(response_times) if response_times else 0,
            "avg_response_length": sum(response_lengths) / len(response_lengths) if response_lengths else 0,
            "question_types_distribution": self.metrics["question_types"].copy()
        }
    
    async def _save_to_db(
        self, 
        query: str, 
        response: str, 
        response_time: float,
        from_cache: bool,
        question_type: str
    ):
        """Збереження метрик в БД (асинхронно)"""
        try:
            from database import db
            if not db.pool:
                return
            
            # Створюємо таблицю для метрик (якщо не існує)
            async with db.pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS ai_metrics (
                        id SERIAL PRIMARY KEY,
                        query TEXT,
                        response TEXT,
                        response_time FLOAT,
                        from_cache BOOLEAN,
                        question_type VARCHAR(50),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Зберігаємо метрики
                await conn.execute("""
                    INSERT INTO ai_metrics (query, response, response_time, from_cache, question_type)
                    VALUES ($1, $2, $3, $4, $5)
                """, query[:500] if query else "", response[:1000] if response else "", response_time, from_cache, question_type)
        except Exception as e:
            # Логуємо помилку, але не зупиняємо роботу
            logger.error(f"Помилка збереження метрик в БД: {e}")

