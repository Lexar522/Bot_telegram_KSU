# 🔧 Технічна імплементація оптимізації OLLAMA

## 📦 Структура нових модулів

### 1. Оптимізований клієнт OLLAMA

```python
# ollama_optimized/client.py
import aiohttp
import time
from typing import Optional, Dict, List
from config import OLLAMA_API_URL, OLLAMA_MODEL
from ollama_optimized.prompt_builder import PromptBuilder
from ollama_optimized.context_optimizer import ContextOptimizer
from ollama_optimized.question_classifier import QuestionClassifier
from ollama_optimized.cache import ResponseCache
from ollama_optimized.validators.multi_level import MultiLevelValidator
from ollama_optimized.metrics.collector import MetricsCollector

class OptimizedOllamaClient:
    def __init__(self):
        self.api_url = OLLAMA_API_URL
        self.model = OLLAMA_MODEL
        self.prompt_builder = PromptBuilder()
        self.context_optimizer = ContextOptimizer()
        self.question_classifier = QuestionClassifier()
        self.cache = ResponseCache(max_size=200)
        self.validator = MultiLevelValidator()
        self.metrics = MetricsCollector()
        
        # Адаптивні параметри генерації
        self.generation_params = {
            "factual": {
                "temperature": 0.1,
                "top_p": 0.5,
                "num_predict": 200,
                "repeat_penalty": 1.3,
                "top_k": 30
            },
            "comparison": {
                "temperature": 0.2,
                "top_p": 0.7,
                "num_predict": 600,
                "repeat_penalty": 1.5,
                "top_k": 40
            },
            "admission": {
                "temperature": 0.0,
                "top_p": 0.3,
                "num_predict": 400,
                "repeat_penalty": 1.4,
                "top_k": 20
            },
            "tuition": {
                "temperature": 0.0,
                "top_p": 0.3,
                "num_predict": 300,
                "repeat_penalty": 1.4,
                "top_k": 20
            },
            "default": {
                "temperature": 0.1,
                "top_p": 0.5,
                "num_predict": 350,
                "repeat_penalty": 1.4,
                "top_k": 30
            }
        }
    
    async def generate_response(
        self, 
        prompt: str, 
        context: List[Dict] = None,
        use_cache: bool = True
    ) -> str:
        """
        Оптимізована генерація відповіді з кешуванням та адаптивними параметрами
        """
        start_time = time.time()
        
        # 1. Класифікуємо питання
        question_type = self.question_classifier.classify(prompt)
        
        # 2. Отримуємо оптимізований контекст
        from services.knowledge_service import KnowledgeService
        knowledge_service = KnowledgeService()
        full_context = knowledge_service.get_context_for_prompt(prompt)
        
        optimized_context = self.context_optimizer.optimize_context(
            prompt, 
            full_context["structured_json"]
        )
        
        # 3. Перевіряємо кеш
        if use_cache:
            cached_response = self.cache.get(prompt, optimized_context)
            if cached_response:
                response_time = time.time() - start_time
                self.metrics.record_request(
                    prompt, cached_response, response_time, from_cache=True
                )
                return cached_response
        
        # 4. Формуємо оптимізований промпт
        system_prompt = self.prompt_builder.build_system_prompt(
            question_type, 
            optimized_context
        )
        
        full_prompt = f"{system_prompt}\n\nПИТАННЯ: {prompt}\n\nВІДПОВІДЬ:"
        
        # 5. Отримуємо параметри генерації
        params = self.generation_params.get(
            question_type, 
            self.generation_params["default"]
        )
        
        # 6. Генеруємо відповідь
        response = await self._generate_with_retry(
            full_prompt, 
            params, 
            max_retries=3
        )
        
        # 7. Валідуємо відповідь
        validation_result = self.validator.validate(response, prompt)
        
        if not validation_result.is_valid:
            # Регенеруємо з більш суворими параметрами
            params["temperature"] = 0.0
            params["top_p"] = 0.2
            response = await self._generate_with_retry(
                full_prompt, 
                params, 
                max_retries=2
            )
            
            # Повторна валідація
            validation_result = self.validator.validate(response, prompt)
        
        # 8. Зберігаємо в кеш
        if validation_result.is_valid and use_cache:
            self.cache.set(prompt, optimized_context, response)
        
        # 9. Записуємо метрики
        response_time = time.time() - start_time
        self.metrics.record_request(
            prompt, response, response_time, from_cache=False
        )
        
        return response
    
    async def _generate_with_retry(
        self, 
        prompt: str, 
        params: Dict, 
        max_retries: int = 3
    ) -> str:
        """Генерація з повторними спробами"""
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    payload = {
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": params
                    }
                    
                    async with session.post(
                        f"{self.api_url}/api/generate",
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=60)
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            answer = data.get("response", "").strip()
                            if answer:
                                return answer
                        
                        if attempt < max_retries - 1:
                            await asyncio.sleep(1)  # Затримка перед повторною спробою
                            
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                await asyncio.sleep(1)
        
        return "Вибач, не вдалося отримати відповідь. Спробуй переформулювати питання."
```

---

### 2. Побудова промптів

```python
# ollama_optimized/prompt_builder.py
from typing import Dict

class PromptBuilder:
    """Побудова оптимізованих промптів"""
    
    # Базові інструкції (короткі)
    BASE_INSTRUCTIONS = """Ти - помічник абітурієнта Херсонського державного університету (ХДУ).
Відповідай ТІЛЬКИ про ХДУ. Використовуй ТІЛЬКИ інформацію з бази знань.
Будь коротким (2-4 речення), точним, дружнім."""
    
    # Роль та обмеження
    ROLE_DEFINITION = """🎯 РОЛЬ:
- Відповідай ТІЛЬКИ про ХДУ
- НІКОЛИ не згадуй інші університети
- Використовуй ТІЛЬКИ дані з бази знань
- Якщо немає даних - чесно скажи"""
    
    # Обмеження
    CONSTRAINTS = """🚫 ЗАБОРОНА:
- ХНТУ, ХНУ, КНУ, Львівський, Одеський, Білосток, Міцкевич
- Російські/англійські слова
- Вигадана інформація"""
    
    # Приклади для різних типів питань
    FEW_SHOT_EXAMPLES = {
        "factual": """
Питання: "Які є факультети?"
Відповідь: "В ХДУ є 8 факультетів: Факультет української й іноземної філології, журналістики та мистецтв; Факультет психології, історії та соціології; Медичний факультет; Факультет біології, географії та екології; Факультет фізичного виховання та спорту; Педагогічний факультет; Факультет бізнесу і права; Факультет комп'ютерних наук, фізики та математики. Обери факультет для перегляду спеціальностей 🎓"
""",
        "tuition": """
Питання: "Скільки коштує навчання на психолога?"
Відповідь: "Вартість навчання на Психологію в ХДУ: Бакалавр (денна) - 3683 грн/місяць, 18415 грн/семестр, 36830 грн/рік. Магістр (денна) - 4788 грн/місяць, 23940 грн/семестр, 47880 грн/рік. Для уточнення: +380 552 494375 💰"
""",
        "admission": """
Питання: "Які документи потрібні для вступу?"
Відповідь: "Для вступу до ХДУ потрібні: заява, документ про освіту, фото 3x4 (4 шт.), копія паспорта, копія ідентифікаційного коду, медична довідка (форма 086-о), результати ЗНО. Детальніше: +380 552 494375 📞"
"""
    }
    
    def build_system_prompt(self, question_type: str, context: Dict) -> str:
        """Побудова системного промпту"""
        # Базові інструкції
        prompt_parts = [self.BASE_INSTRUCTIONS, self.ROLE_DEFINITION, self.CONSTRAINTS]
        
        # Додаємо приклади для типу питання
        if question_type in self.FEW_SHOT_EXAMPLES:
            prompt_parts.append(f"💡 ПРИКЛАДИ:\n{self.FEW_SHOT_EXAMPLES[question_type]}")
        
        # Додаємо оптимізований контекст
        context_text = self._format_context(context)
        prompt_parts.append(f"📚 БАЗА ЗНАНЬ:\n{context_text}")
        
        # Інструкції з самоперевірки
        prompt_parts.append(self._get_self_check_instructions())
        
        return "\n\n".join(prompt_parts)
    
    def _format_context(self, context: Dict) -> str:
        """Форматування контексту для промпту"""
        # Обмежуємо розмір контексту
        import json
        context_str = json.dumps(context, ensure_ascii=False, indent=2)
        
        # Якщо контекст занадто великий, обрізаємо
        max_context_length = 2000  # токенів
        if len(context_str) > max_context_length:
            # Залишаємо тільки важливі секції
            important_keys = ["university", "contacts", "admission", "documents"]
            filtered_context = {
                k: v for k, v in context.items() 
                if k in important_keys or any(ik in k for ik in important_keys)
            }
            context_str = json.dumps(filtered_context, ensure_ascii=False, indent=2)
        
        return context_str
    
    def _get_self_check_instructions(self) -> str:
        """Інструкції для самоперевірки"""
        return """✅ САМОПЕРЕВІРКА ПЕРЕД ВІДПРАВКОЮ:
1. Чи немає заборонених університетів?
2. Чи правильна орфографія?
3. Чи використано ТІЛЬКИ дані з бази знань?
4. Чи відповідь структурована (2-4 речення)?

Якщо знайдено помилки - виправ та сформуй відповідь знову."""
```

---

### 3. Оптимізація контексту

```python
# ollama_optimized/context_optimizer.py
from typing import Dict, List
import re

class ContextOptimizer:
    """Оптимізація контексту для зменшення використання токенів"""
    
    MAX_CONTEXT_TOKENS = 2000  # Максимальна кількість токенів в контексті
    
    # Пріоритети секцій
    SECTION_PRIORITY = {
        "high": ["university", "contacts", "admission.year_2026", "documents"],
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
        prioritized = self._prioritize_sections(relevant_sections)
        
        # 4. Обмежуємо розмір
        optimized = self._limit_context_size(prioritized)
        
        # 5. Завжди додаємо важливі секції
        optimized["university"] = full_knowledge.get("university", {})
        optimized["contacts"] = full_knowledge.get("contacts", {})
        
        return optimized
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Витягування ключових слів з запиту"""
        # Видаляємо стоп-слова
        stop_words = {"як", "що", "де", "коли", "чи", "для", "про", "на", "в", "з"}
        
        words = re.findall(r'\b\w+\b', query.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        return keywords
    
    def _find_relevant_sections(self, keywords: List[str], knowledge: Dict) -> Dict:
        """Пошук релевантних секцій"""
        relevant = {}
        
        for section_key, section_data in knowledge.items():
            section_str = str(section_data).lower()
            
            # Рахуємо збіги ключових слів
            matches = sum(1 for kw in keywords if kw in section_str)
            
            if matches > 0:
                relevant[section_key] = {
                    "data": section_data,
                    "relevance_score": matches / len(keywords) if keywords else 0
                }
        
        return relevant
    
    def _prioritize_sections(self, sections: Dict) -> Dict:
        """Пріоритизація секцій"""
        prioritized = {}
        
        # Спочатку додаємо секції з високим пріоритетом
        for priority_level in ["high", "medium", "low"]:
            for section_key in self.SECTION_PRIORITY[priority_level]:
                if section_key in sections:
                    prioritized[section_key] = sections[section_key]["data"]
        
        # Потім додаємо інші релевантні секції
        for section_key, section_info in sections.items():
            if section_key not in prioritized:
                prioritized[section_key] = section_info["data"]
        
        return prioritized
    
    def _limit_context_size(self, context: Dict) -> Dict:
        """Обмеження розміру контексту"""
        import json
        
        # Перевіряємо розмір
        context_str = json.dumps(context, ensure_ascii=False)
        estimated_tokens = len(context_str) // 4  # Приблизна оцінка
        
        if estimated_tokens <= self.MAX_CONTEXT_TOKENS:
            return context
        
        # Якщо занадто великий - обрізаємо низькопріоритетні секції
        limited = {}
        current_tokens = 0
        
        for priority_level in ["high", "medium", "low"]:
            for section_key in self.SECTION_PRIORITY[priority_level]:
                if section_key in context:
                    section_str = json.dumps(context[section_key], ensure_ascii=False)
                    section_tokens = len(section_str) // 4
                    
                    if current_tokens + section_tokens <= self.MAX_CONTEXT_TOKENS:
                        limited[section_key] = context[section_key]
                        current_tokens += section_tokens
                    else:
                        break
        
        return limited
```

---

### 4. Класифікація питань

```python
# ollama_optimized/question_classifier.py
import re
from typing import Dict

class QuestionClassifier:
    """Класифікація питань для вибору оптимальної стратегії"""
    
    QUESTION_PATTERNS = {
        "factual": [
            r"які\s+є", r"що\s+таке", r"де\s+знаходиться",
            r"скільки\s+є", r"які\s+спеціальності"
        ],
        "comparison": [
            r"порівняй", r"в\s+чому\s+різниця", r"що\s+краще",
            r"яка\s+різниця", r"скільки\s+різних"
        ],
        "procedural": [
            r"як\s+подати", r"які\s+кроки", r"що\s+потрібно\s+зробити",
            r"як\s+вступити", r"як\s+підготуватися"
        ],
        "admission": [
            r"вступ", r"нмт", r"документ", r"кампанія",
            r"правила\s+вступу", r"траєкторії"
        ],
        "tuition": [
            r"вартість", r"ціна", r"скільки\s+коштує",
            r"оплата", r"тарифи"
        ],
        "faculties": [
            r"факультет", r"спеціальність", r"напрям",
            r"освітні\s+програми"
        ]
    }
    
    def classify(self, query: str) -> str:
        """Класифікація питання"""
        query_lower = query.lower()
        
        # Перевіряємо специфічні типи (в порядку пріоритету)
        for q_type, patterns in self.QUESTION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return q_type
        
        # За замовчуванням - фактичне питання
        return "factual"
    
    def get_confidence(self, query: str, question_type: str) -> float:
        """Оцінка впевненості в класифікації"""
        query_lower = query.lower()
        patterns = self.QUESTION_PATTERNS.get(question_type, [])
        
        matches = sum(1 for pattern in patterns if re.search(pattern, query_lower))
        total_patterns = len(patterns)
        
        return matches / total_patterns if total_patterns > 0 else 0.0
```

---

### 5. Кешування відповідей

```python
# ollama_optimized/cache.py
import hashlib
import json
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
            f"{normalized_query}:{context_hash}".encode()
        ).hexdigest()
    
    def _normalize_query(self, query: str) -> str:
        """Нормалізація запиту для кешу"""
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
        context_hash = hashlib.md5(
            json.dumps(context, sort_keys=True).encode()
        ).hexdigest()
        
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
        # Якщо кеш переповнений - видаляємо найстаріший
        if len(self.cache) >= self.max_size:
            oldest_key = min(
                self.cache.keys(),
                key=lambda k: self.cache[k]["timestamp"]
            )
            del self.cache[oldest_key]
        
        context_hash = hashlib.md5(
            json.dumps(context, sort_keys=True).encode()
        ).hexdigest()
        
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
            "usage_percent": (len(self.cache) / self.max_size) * 100
        }
```

---

### 6. Багаторівнева валідація

```python
# ollama_optimized/validators/multi_level.py
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
        all_errors = []
        total_weight = 0
        
        for level in self.levels:
            result = level.validator(response, query)
            if not result.is_valid:
                # Зважуємо помилки за важливістю рівня
                weighted_errors = [
                    f"[{level.name}] {error}" 
                    for error in result.errors
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
        
        return ValidationResult(is_valid=True)
    
    def _detailed_validation(self, response: str, query: str) -> ValidationResult:
        """Детальна перевірка"""
        return self.base_validator.validate(response)
    
    def _semantic_validation(self, response: str, query: str) -> ValidationResult:
        """Семантична перевірка релевантності"""
        query_lower = query.lower()
        response_lower = response.lower()
        
        # Витягуємо ключові слова з питання
        query_keywords = self._extract_keywords(query)
        
        # Перевіряємо наявність ключових слів у відповіді
        found_keywords = sum(
            1 for kw in query_keywords 
            if kw in response_lower
        )
        
        # Якщо менше 30% ключових слів знайдено - відповідь нерелевантна
        if query_keywords and found_keywords / len(query_keywords) < 0.3:
            return ValidationResult(
                is_valid=False,
                errors=["Відповідь не відповідає на питання"]
            )
        
        return ValidationResult(is_valid=True)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Витягування ключових слів"""
        import re
        stop_words = {"як", "що", "де", "коли", "чи", "для", "про"}
        words = re.findall(r'\b\w+\b', text.lower())
        return [w for w in words if w not in stop_words and len(w) > 2]
```

---

### 7. Збір метрик

```python
# ollama_optimized/metrics/collector.py
from typing import Dict, List
from datetime import datetime
from database import db

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
        
        self.metrics["response_times"].append(response_time)
        self.metrics["response_lengths"].append(len(response))
        
        # Зберігаємо в БД для аналізу
        self._save_to_db(query, response, response_time, from_cache, question_type)
    
    def get_statistics(self) -> Dict:
        """Отримання статистики"""
        total = self.metrics["total_requests"]
        
        if total == 0:
            return {}
        
        return {
            "total_requests": total,
            "cache_hit_rate": self.metrics["cache_hits"] / total * 100,
            "validation_failure_rate": self.metrics["validation_failures"] / total * 100,
            "avg_response_time": sum(self.metrics["response_times"]) / len(self.metrics["response_times"]) if self.metrics["response_times"] else 0,
            "avg_response_length": sum(self.metrics["response_lengths"]) / len(self.metrics["response_lengths"]) if self.metrics["response_lengths"] else 0,
            "question_types_distribution": self.metrics["question_types"]
        }
    
    async def _save_to_db(
        self, 
        query: str, 
        response: str, 
        response_time: float,
        from_cache: bool,
        question_type: str
    ):
        """Збереження метрик в БД"""
        try:
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
                """, query[:500], response[:1000], response_time, from_cache, question_type)
        except Exception as e:
            # Логуємо помилку, але не зупиняємо роботу
            import logging
            logging.error(f"Помилка збереження метрик: {e}")
```

---

## 🔄 Інтеграція з існуючим кодом

### Оновлення `ollama_client.py`:

```python
# ollama_client.py (оновлена версія)
from ollama_optimized.client import OptimizedOllamaClient

# Замінюємо старий клієнт
ollama = OptimizedOllamaClient()

# Використання залишається таким самим
response = await ollama.generate_response(user_message, context_list)
```

---

## 📊 Тестування

### Unit-тести:

```python
# tests/test_ollama_optimized.py
import pytest
from ollama_optimized.client import OptimizedOllamaClient
from ollama_optimized.question_classifier import QuestionClassifier

def test_question_classification():
    classifier = QuestionClassifier()
    
    assert classifier.classify("Які є факультети?") == "faculties"
    assert classifier.classify("Скільки коштує навчання?") == "tuition"
    assert classifier.classify("Як вступити?") == "procedural"

def test_cache():
    cache = ResponseCache()
    query = "Які є факультети?"
    context = {"faculties": {}}
    response = "В ХДУ є 8 факультетів..."
    
    cache.set(query, context, response)
    assert cache.get(query, context) == response
```

---

## 🚀 Початок використання

1. **Створіть структуру папок:**
```bash
mkdir -p ollama_optimized/validators
mkdir -p ollama_optimized/metrics
mkdir -p ollama_optimized/handlers
```

2. **Створіть файли** згідно з прикладами вище

3. **Оновіть імпорти** в `main.py` та `handlers.py`

4. **Запустіть тести** для перевірки

5. **Моніторьте метрики** для аналізу покращень

---

**Готово до імплементації!** 🎉

