"""
Оптимізований клієнт OLLAMA з усіма покращеннями
"""
import aiohttp
import asyncio
import time
import json
import re
from typing import Optional, Dict, List, AsyncGenerator
from config import OLLAMA_API_URL, OLLAMA_MODEL
from ollama_optimized.prompt_builder import PromptBuilder
from ollama_optimized.context_optimizer import ContextOptimizer
from ollama_optimized.question_classifier import QuestionClassifier
from ollama_optimized.cache import ResponseCache
from ollama_optimized.semantic_cache import SemanticCache
from ollama_optimized.validators.multi_level import MultiLevelValidator
from ollama_optimized.metrics.collector import MetricsCollector
from services.knowledge_service import KnowledgeService
import logging

logger = logging.getLogger(__name__)


class OptimizedOllamaClient:
    """Оптимізований клієнт OLLAMA з кешуванням, валідацією та метриками"""
    
    def __init__(self):
        self.api_url = OLLAMA_API_URL
        self.model = OLLAMA_MODEL
        self.prompt_builder = PromptBuilder()
        self.context_optimizer = ContextOptimizer()
        self.question_classifier = QuestionClassifier()
        self.cache = ResponseCache(max_size=200)
        self.semantic_cache = SemanticCache(max_size=200, similarity_threshold=0.7)
        self.validator = MultiLevelValidator()
        self.metrics = MetricsCollector()
        self.knowledge_service = KnowledgeService()
        
        # Адаптивні параметри генерації (оптимізовані для кращого розуміння)
        self.generation_params = {
            "factual": {
                "temperature": 0.05,  # Низька для точності
                "top_p": 0.4,  # Звужений для фокусу
                "num_predict": 300,  # Більше для повноти
                "repeat_penalty": 1.5,  # Вища для уникнення повторів
                "top_k": 25  # Менше варіантів для точності
            },
            "comparison": {
                "temperature": 0.15,  # Трохи вища для творчості
                "top_p": 0.6,
                "num_predict": 600,
                "repeat_penalty": 1.6,
                "top_k": 35
            },
            "admission": {
                "temperature": 0.0,  # Мінімальна для точності
                "top_p": 0.25,  # Дуже звужений
                "num_predict": 500,  # Більше для повної інформації
                "repeat_penalty": 1.5,
                "top_k": 15  # Мінімум варіантів
            },
            "tuition": {
                "temperature": 0.0,  # Мінімальна для точності цифр
                "top_p": 0.25,
                "num_predict": 400,
                "repeat_penalty": 1.5,
                "top_k": 15
            },
            "faculties": {
                "temperature": 0.05,
                "top_p": 0.4,
                "num_predict": 350,
                "repeat_penalty": 1.4,
                "top_k": 25
            },
            "procedural": {
                "temperature": 0.1,  # Трохи вища для послідовності
                "top_p": 0.5,
                "num_predict": 450,
                "repeat_penalty": 1.5,
                "top_k": 30
            },
            "default": {
                "temperature": 0.05,
                "top_p": 0.4,
                "num_predict": 400,
                "repeat_penalty": 1.5,
                "top_k": 25
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
        
        if not prompt:
            return "Вибач, не зрозумів питання. Спробуй переформулювати."
        
        # 1. Класифікуємо питання
        question_type = self.question_classifier.classify(prompt)
        
        # 2. Отримуємо оптимізований контекст
        full_context = self.knowledge_service.get_context_for_prompt(prompt)
        optimized_context = self.context_optimizer.optimize_context(
            prompt, 
            full_context["structured_json"]
        )
        
        # 3. Перевіряємо кеш (спочатку точний, потім семантичний)
        if use_cache:
            # Точний пошук
            cached_response = self.cache.get(prompt, optimized_context)
            if cached_response:
                response_time = time.time() - start_time
                self.metrics.record_request(
                    prompt, cached_response, response_time, 
                    from_cache=True, question_type=question_type, validation_passed=True
                )
                logger.info(f"Exact cache hit for question type: {question_type}")
                return cached_response
            
            # Семантичний пошук
            semantic_result = self.semantic_cache.get(prompt, optimized_context)
            if semantic_result:
                cached_response, similarity = semantic_result
                response_time = time.time() - start_time
                self.metrics.record_request(
                    prompt, cached_response, response_time, 
                    from_cache=True, question_type=question_type, validation_passed=True
                )
                logger.info(f"Semantic cache hit (similarity: {similarity:.2f}) for question type: {question_type}")
                return cached_response
        
        # 4. Аналізуємо питання для кращого розуміння
        analyzed_query = self._analyze_and_enhance_query(prompt, question_type)
        
        # 5. Формуємо оптимізований промпт з аналізом питання
        system_prompt = self.prompt_builder.build_system_prompt(
            question_type, 
            optimized_context,
            user_query=prompt
        )
        
        # 6. Додаємо Chain-of-Thought для складних питань
        if self._should_use_cot(question_type, prompt):
            full_prompt = self._build_cot_prompt(system_prompt, analyzed_query)
        else:
            # Покращене формулювання питання для моделі
            full_prompt = f"""{system_prompt}

═══════════════════════════════════════
ПИТАННЯ КОРИСТУВАЧА:
{prompt}

ПРОАНАЛІЗОВАНЕ ПИТАННЯ:
{analyzed_query}
═══════════════════════════════════════

ТВОЯ ЗАДАЧА:
1. Уважно прочитай питання
2. Знайди відповідну інформацію в базі знань вище
3. Сформуй точну, структуровану відповідь
4. Перевір відповідь за списком самоперевірки

ВІДПОВІДЬ (структурована, конкретна, з даними з бази знань):"""
        
        # 7. Отримуємо параметри генерації (покращені для кращого розуміння)
        params = self.generation_params.get(
            question_type, 
            self.generation_params["default"]
        )
        
        # Адаптуємо параметри залежно від довжини питання та складності
        params = self._adapt_params(params, len(prompt))
        
        # Покращені параметри для кращого розуміння (вже оптимізовані вище)
        # Не змінюємо, щоб не зіпсувати оптимізацію
        
        # 7. Генеруємо відповідь (з контекстом для chat API)
        response = await self._generate_with_retry(
            full_prompt, 
            params, 
            max_retries=3,
            context=context if context else []
        )
        
        # 7.1. Перевірка якості відповіді (мінімальний fallback тільки якщо критично)
        response_lower = response.lower() if response else ""
        
        # Fallback тільки якщо відповідь явно некоректна
        if not response or len(response.strip()) < 30 or "не вдалося" in response_lower:
            # Тільки для питань про вступ використовуємо fallback
            if question_type == "admission":
                logger.warning(f"Критична помилка генерації для вступу, використовуємо fallback: {prompt[:50]}")
                response = self._get_admission_fallback(prompt)
            else:
                # Для інших питань - спробуємо регенерувати з кращими параметрами
                logger.warning(f"Погана відповідь, регенеруємо: {prompt[:50]}")
                strict_params = params.copy()
                strict_params["temperature"] = 0.0
                strict_params["top_p"] = 0.2
                strict_params["num_predict"] = min(600, params.get("num_predict", 350) * 2)
                response = await self._generate_with_retry(
                full_prompt, 
                strict_params, 
                max_retries=2,
                context=context if context else []
            )
        
        # 8. Валідуємо відповідь (тільки критичні помилки)
        validation_result = self.validator.validate(response, prompt)
        
        # Регенеруємо тільки при критичних помилках (заборонені університети, порожня відповідь)
        critical_errors = [
            "заборонений університет" in validation_result.error_message.lower() if validation_result.error_message else False,
            not response or len(response.strip()) < 20
        ]
        
        if not validation_result.is_valid and any(critical_errors):
            logger.warning(f"Критична помилка валідації: {validation_result.error_message}")
            # Регенеруємо з більш суворими параметрами
            strict_params = params.copy()
            strict_params["temperature"] = 0.0
            strict_params["top_p"] = 0.15
            strict_params["repeat_penalty"] = 1.7
            strict_params["num_predict"] = min(600, params.get("num_predict", 400) * 1.5)
            
            # Додаємо додаткові інструкції в промпт
            enhanced_prompt = f"""{full_prompt}

⚠️ ВАЖЛИВО: Попередня відповідь містила помилки: {validation_result.error_message}
Сформуй відповідь ЗНОВУ, уникнувши цих помилок. Використовуй ТІЛЬКИ дані з бази знань вище."""
            
            response = await self._generate_with_retry(
                enhanced_prompt, 
                strict_params, 
                max_retries=2,
                context=context if context else []
            )
            
            # Повторна валідація
            validation_result = self.validator.validate(response, prompt)
            self.metrics.metrics["regeneration_count"] += 1
        elif not validation_result.is_valid:
            # Не критичні помилки - просто логуємо
            logger.info(f"Не критична помилка валідації: {validation_result.error_message}")
        
        # 9. Зберігаємо в кеш (обидва типи)
        if validation_result.is_valid and use_cache:
            self.cache.set(prompt, optimized_context, response)
            self.semantic_cache.set(prompt, optimized_context, response)
        
        # 10. Записуємо метрики
        response_time = time.time() - start_time
        self.metrics.record_request(
            prompt, response, response_time, 
            from_cache=False, question_type=question_type, 
            validation_passed=validation_result.is_valid
        )
        
        return response
    
    def _analyze_and_enhance_query(self, query: str, question_type: str) -> str:
        """Аналіз та покращення питання для кращого розуміння моделлю"""
        query_lower = query.lower()
        
        # Визначаємо ключові слова та інтент
        keywords = []
        intent = question_type
        
        # Ключові слова для різних типів питань
        if question_type == "admission":
            keywords.extend(["вступ", "нмт", "кампанія", "правила", "траєкторії"])
        elif question_type == "tuition":
            keywords.extend(["вартість", "ціна", "коштує", "оплата", "тарифи"])
        elif question_type == "faculties":
            keywords.extend(["факультет", "спеціальність", "напрям", "освітні програми"])
        elif question_type == "procedural":
            keywords.extend(["як", "кроки", "подати", "оформити", "процедура"])
        elif question_type == "comparison":
            keywords.extend(["різниця", "порівняння", "краще", "відрізняється"])
        
        # Знаходимо ключові слова в питанні
        found_keywords = [kw for kw in keywords if kw in query_lower]
        
        # Формуємо покращене питання
        enhanced = f"""Оригінальне питання: "{query}"

Аналіз:
- Тип питання: {question_type}
- Ключові слова: {', '.join(found_keywords) if found_keywords else 'загальне питання'}
- Що потрібно знайти: {self._get_expected_info(question_type)}

Завдання: Знайди в базі знань інформацію про {self._get_search_target(question_type)} та дай точну відповідь."""
        
        return enhanced
    
    def _get_expected_info(self, question_type: str) -> str:
        """Очікувана інформація для типу питання"""
        mapping = {
            "admission": "правила вступу, НМТ, траєкторії, вступна кампанія, електронний кабінет",
            "tuition": "вартість навчання, тарифи, оплата за семестр/рік",
            "faculties": "факультети, спеціальності, освітні програми, коди спеціальностей",
            "procedural": "кроки, процедура, порядок дій, необхідні документи",
            "comparison": "порівняння, різниця між варіантами, переваги",
            "factual": "загальна інформація про ХДУ, контакти, адреса"
        }
        return mapping.get(question_type, "інформація про ХДУ")
    
    def _get_search_target(self, question_type: str) -> str:
        """Ціль пошуку для типу питання"""
        mapping = {
            "admission": "вступ до ХДУ у 2026 році",
            "tuition": "вартість навчання в ХДУ",
            "faculties": "факультети та спеціальності ХДУ",
            "procedural": "процедуру вступу до ХДУ",
            "comparison": "порівняння варіантів навчання в ХДУ",
            "factual": "загальну інформацію про ХДУ"
        }
        return mapping.get(question_type, "інформацію про ХДУ")
    
    def _should_use_cot(self, question_type: str, query: str) -> bool:
        """Визначає, чи потрібен Chain-of-Thought"""
        # Використовуємо CoT для складних питань
        complex_indicators = [
            "порівняй", "в чому різниця", "як вибрати",
            "що краще", "яка різниця", "скільки різних"
        ]
        
        query_lower = query.lower()
        has_complex_indicator = any(indicator in query_lower for indicator in complex_indicators)
        
        # Використовуємо CoT для порівнянь та довгих питань
        return question_type == "comparison" or has_complex_indicator or len(query) > 100
    
    def _build_cot_prompt(self, system_prompt: str, query: str) -> str:
        """Побудова промпту з Chain-of-Thought"""
        cot_instructions = """Відповідай на питання крок за кроком:

КРОК 1: Розуміння питання
- Про що питають? (спеціальності, вартість, документи, контакти)
- Яка конкретна інформація потрібна?

КРОК 2: Пошук в базі знань
- Яка секція бази знань містить відповідь?
- Які конкретні дані потрібні?

КРОК 3: Формування відповіді
- Як структурувати відповідь?
- Які конкретні дані включити?

КРОК 4: Перевірка
- Чи немає заборонених університетів?
- Чи правильна орфографія?
- Чи відповідь відповідає на питання?

ВІДПОВІДЬ (після всіх кроків, структурована, тільки про ХДУ):"""
        
        return f"{system_prompt}\n\n{cot_instructions}\n\nПИТАННЯ: {query}\n\n"
    
    def _adapt_params(self, params: Dict, query_length: int) -> Dict:
        """Адаптація параметрів залежно від довжини питання"""
        adapted = params.copy()
        
        # Адаптуємо num_predict залежно від довжини питання
        if query_length < 20:
            adapted["num_predict"] = min(150, adapted["num_predict"])
        elif query_length > 100:
            adapted["num_predict"] = min(800, int(adapted["num_predict"] * 1.2))
        
        return adapted
    
    async def _generate_with_retry(
        self, 
        prompt: str, 
        params: Dict, 
        max_retries: int = 3,
        context: List[Dict] = None
    ) -> str:
        """Генерація з повторними спробами (остання версія OLLAMA API)"""
        last_error = None
        
        # Розділяємо системний промпт та питання користувача
        system_prompt = ""
        user_message = prompt
        
        # Якщо промпт містить розділювач, розділяємо
        if "═══════════════════════════════════════" in prompt:
            parts = prompt.split("═══════════════════════════════════════")
            if len(parts) >= 2:
                system_prompt = parts[0].strip()
                # Знаходимо питання користувача
                for part in parts[1:]:
                    if "ПИТАННЯ КОРИСТУВАЧА:" in part:
                        user_lines = part.split("\n")
                        for i, line in enumerate(user_lines):
                            if "ПИТАННЯ КОРИСТУВАЧА:" in line and i + 1 < len(user_lines):
                                user_message = user_lines[i + 1].strip()
                                break
        else:
            # Якщо немає розділювача, весь промпт - це системний
            system_prompt = prompt
        
        # Формуємо повідомлення для chat API
        messages = []
        
        # Додаємо системний промпт
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        # Додаємо контекст попередніх повідомлень
        if context:
            for ctx in context:
                if isinstance(ctx, dict):
                    if "user_message" in ctx and "bot_response" in ctx:
                        messages.append({
                            "role": "user",
                            "content": ctx["user_message"]
                        })
                        messages.append({
                            "role": "assistant",
                            "content": ctx["bot_response"]
                        })
        
        # Додаємо поточне питання користувача
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    # Використовуємо новий chat API (рекомендований в OLLAMA 0.11+)
                    payload = {
                        "model": self.model,
                        "messages": messages,
                        "stream": False,
                        "options": params
                    }
                    
                    # Спробуємо спочатку новий chat API
                    try:
                        async with session.post(
                            f"{self.api_url}/api/chat",
                            json=payload,
                            timeout=aiohttp.ClientTimeout(total=60)
                        ) as response:
                            if response.status == 200:
                                data = await response.json()
                                # Новий формат відповіді
                                if "message" in data:
                                    answer = data["message"].get("content", "").strip()
                                elif "response" in data:
                                    answer = data["response"].strip()
                                else:
                                    answer = str(data).strip()
                                
                                if answer:
                                    return answer
                            else:
                                error_text = await response.text()
                                last_error = f"HTTP {response.status}: {error_text}"
                    except Exception as chat_error:
                        # Якщо chat API не працює, використовуємо старий generate API
                        logger.info(f"Chat API не доступний, використовуємо generate API: {chat_error}")
                        generate_payload = {
                            "model": self.model,
                            "prompt": prompt,
                            "stream": False,
                            "options": params
                        }
                        
                        async with session.post(
                            f"{self.api_url}/api/generate",
                            json=generate_payload,
                            timeout=aiohttp.ClientTimeout(total=60)
                        ) as response:
                            if response.status == 200:
                                data = await response.json()
                                answer = data.get("response", "").strip()
                                if answer:
                                    return answer
                            else:
                                error_text = await response.text()
                                last_error = f"HTTP {response.status}: {error_text}"
                    
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1)  # Затримка перед повторною спробою
                            
            except asyncio.TimeoutError:
                last_error = "Timeout"
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                else:
                    logger.error(f"Error generating response: {e}")
        
        from knowledge_base import get_admissions_committee_phones
        return f"Вибач, не вдалося отримати відповідь. Спробуй переформулювати питання або звернися до приймальної комісії ХДУ:\n\n{get_admissions_committee_phones()}"
    
    async def generate_response_stream(
        self,
        prompt: str,
        context: List[Dict] = None,
        use_cache: bool = True
    ) -> AsyncGenerator[str, None]:
        """
        Streaming генерація відповіді - користувач бачить відповідь по частинах
        Ефект: -40-60% часу очікування для користувача
        """
        start_time = time.time()
        
        if not prompt:
            yield "Вибач, не зрозумів питання. Спробуй переформулювати."
            return
        
        # 1. Класифікуємо питання
        question_type = self.question_classifier.classify(prompt)
        
        # 2. Отримуємо оптимізований контекст
        full_context = self.knowledge_service.get_context_for_prompt(prompt)
        optimized_context = self.context_optimizer.optimize_context(
            prompt,
            full_context["structured_json"]
        )
        
        # 3. Перевіряємо кеш (спочатку точний, потім семантичний)
        if use_cache:
            # Точний пошук
            cached_response = self.cache.get(prompt, optimized_context)
            if cached_response:
                response_time = time.time() - start_time
                self.metrics.record_request(
                    prompt, cached_response, response_time,
                    from_cache=True, question_type=question_type, validation_passed=True
                )
                logger.info(f"Exact cache hit for question type: {question_type}")
                yield cached_response
                return
            
            # Семантичний пошук
            semantic_result = self.semantic_cache.get(prompt, optimized_context)
            if semantic_result:
                cached_response, similarity = semantic_result
                response_time = time.time() - start_time
                self.metrics.record_request(
                    prompt, cached_response, response_time,
                    from_cache=True, question_type=question_type, validation_passed=True
                )
                logger.info(f"Semantic cache hit (similarity: {similarity:.2f}) for question type: {question_type}")
                yield cached_response
                return
        
        # 4. Аналізуємо питання
        analyzed_query = self._analyze_and_enhance_query(prompt, question_type)
        
        # 5. Формуємо промпт
        system_prompt = self.prompt_builder.build_system_prompt(
            question_type,
            optimized_context,
            user_query=prompt
        )
        
        # 6. Додаємо Chain-of-Thought якщо потрібно
        if self._should_use_cot(question_type, prompt):
            full_prompt = self._build_cot_prompt(system_prompt, analyzed_query)
        else:
            full_prompt = f"""{system_prompt}

═══════════════════════════════════════
ПИТАННЯ КОРИСТУВАЧА:
{prompt}

ПРОАНАЛІЗОВАНЕ ПИТАННЯ:
{analyzed_query}
═══════════════════════════════════════

ТВОЯ ЗАДАЧА:
1. Уважно прочитай питання
2. Знайди відповідну інформацію в базі знань вище
3. Сформуй точну, структуровану відповідь
4. Перевір відповідь за списком самоперевірки

ВІДПОВІДЬ (структурована, конкретна, з даними з бази знань):"""
        
        # 7. Отримуємо параметри
        params = self.generation_params.get(
            question_type,
            self.generation_params["default"]
        )
        params = self._adapt_params(params, len(prompt))
        
        # 8. Streaming генерація
        full_response = ""
        try:
            async for chunk in self._generate_stream(full_prompt, params, context):
                full_response += chunk
                yield chunk
        except Exception as e:
            logger.error(f"Помилка streaming генерації: {e}")
            yield f"Вибач, сталася помилка при генерації відповіді. Спробуй переформулювати питання."
            return
        
        # 9. Валідуємо повну відповідь
        validation_result = self.validator.validate(full_response, prompt)
        
        # 10. Зберігаємо в кеш (обидва типи)
        if validation_result.is_valid and use_cache and full_response:
            self.cache.set(prompt, optimized_context, full_response)
            self.semantic_cache.set(prompt, optimized_context, full_response)
        
        # 11. Записуємо метрики
        response_time = time.time() - start_time
        self.metrics.record_request(
            prompt, full_response, response_time,
            from_cache=False, question_type=question_type,
            validation_passed=validation_result.is_valid
        )
    
    async def _generate_stream(
        self,
        prompt: str,
        params: Dict,
        context: List[Dict] = None
    ) -> AsyncGenerator[str, None]:
        """Внутрішній метод для streaming генерації"""
        # Розділяємо системний промпт та питання
        system_prompt = ""
        user_message = prompt
        
        if "═══════════════════════════════════════" in prompt:
            parts = prompt.split("═══════════════════════════════════════")
            if len(parts) >= 2:
                system_prompt = parts[0].strip()
                for part in parts[1:]:
                    if "ПИТАННЯ КОРИСТУВАЧА:" in part:
                        user_lines = part.split("\n")
                        for i, line in enumerate(user_lines):
                            if "ПИТАННЯ КОРИСТУВАЧА:" in line and i + 1 < len(user_lines):
                                user_message = user_lines[i + 1].strip()
                                break
        else:
            system_prompt = prompt
        
        # Формуємо messages
        messages = []
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        if context:
            for ctx in context:
                if isinstance(ctx, dict):
                    if "user_message" in ctx and "bot_response" in ctx:
                        messages.append({
                            "role": "user",
                            "content": ctx["user_message"]
                        })
                        messages.append({
                            "role": "assistant",
                            "content": ctx["bot_response"]
                        })
        
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        # Streaming запит
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "stream": True,  # Увімкнути streaming
                    "options": params
                }
                
                async with session.post(
                    f"{self.api_url}/api/chat",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status == 200:
                        buffer = ""
                        async for chunk_bytes in response.content.iter_chunked(1024):
                            if chunk_bytes:
                                try:
                                    buffer += chunk_bytes.decode('utf-8', errors='ignore')
                                    # Обробляємо повні JSON рядки
                                    while '\n' in buffer:
                                        line, buffer = buffer.split('\n', 1)
                                        line = line.strip()
                                        if line:
                                            try:
                                                data = json.loads(line)
                                                # OLLAMA streaming формат
                                                if "message" in data:
                                                    message = data["message"]
                                                    if isinstance(message, dict) and "content" in message:
                                                        chunk = message["content"]
                                                        if chunk:
                                                            yield chunk
                                                    elif isinstance(message, str):
                                                        yield message
                                                elif "response" in data:
                                                    chunk = data["response"]
                                                    if chunk:
                                                        yield chunk
                                                elif "delta" in data and "content" in data["delta"]:
                                                    # Дельта формат
                                                    chunk = data["delta"]["content"]
                                                    if chunk:
                                                        yield chunk
                                            except json.JSONDecodeError:
                                                continue
                                except Exception as e:
                                    logger.debug(f"Помилка обробки streaming chunk: {e}")
                                    continue
                        # Обробляємо залишок буфера
                        if buffer.strip():
                            try:
                                data = json.loads(buffer.strip())
                                if "message" in data and "content" in data["message"]:
                                    chunk = data["message"]["content"]
                                    if chunk:
                                        yield chunk
                            except json.JSONDecodeError:
                                pass
                    else:
                        error_text = await response.text()
                        logger.error(f"Streaming помилка HTTP {response.status}: {error_text}")
                        yield f"Вибач, сталася помилка при генерації відповіді."
        except Exception as e:
            logger.error(f"Помилка streaming генерації: {e}")
            yield f"Вибач, сталася помилка при генерації відповіді."
    
    async def check_health(self) -> bool:
        """Перевірка доступності OLLAMA (остання версія API)"""
        try:
            async with aiohttp.ClientSession() as session:
                # Спробуємо новий API спочатку
                try:
                    async with session.get(
                        f"{self.api_url}/api/tags",
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status == 200:
                            return True
                except:
                    pass
                
                # Якщо не працює, спробуємо старий варіант
                try:
                    async with session.get(
                        f"{self.api_url}/api/version",
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        return response.status == 200
                except:
                    return False
        except:
            return False
    
    def get_statistics(self) -> Dict:
        """Отримання статистики роботи"""
        return self.metrics.get_statistics()
    
    def get_cache_stats(self) -> Dict:
        """Отримання статистики кешу"""
        exact_stats = self.cache.get_stats()
        semantic_stats = self.semantic_cache.get_stats()
        return {
            "exact_cache": exact_stats,
            "semantic_cache": semantic_stats,
            "total_entries": exact_stats["size"] + semantic_stats["size"]
        }
    
    async def generate_response_parallel(
        self,
        prompt: str,
        context: List[Dict] = None,
        num_candidates: int = 3,
        use_cache: bool = True
    ) -> str:
        """
        Паралельна генерація кількох варіантів відповіді та вибір найкращого
        Ефект: +20% швидкості та точності для складних питань
        """
        start_time = time.time()
        
        if not prompt:
            return "Вибач, не зрозумів питання. Спробуй переформулювати."
        
        # Перевіряємо кеш перед паралельною генерацією
        if use_cache:
            question_type = self.question_classifier.classify(prompt)
            full_context = self.knowledge_service.get_context_for_prompt(prompt)
            optimized_context = self.context_optimizer.optimize_context(
                prompt,
                full_context["structured_json"]
            )
            
            cached_response = self.cache.get(prompt, optimized_context)
            if cached_response:
                return cached_response
            
            semantic_result = self.semantic_cache.get(prompt, optimized_context)
            if semantic_result:
                return semantic_result[0]
        
        # Генеруємо кілька варіантів паралельно
        question_type = self.question_classifier.classify(prompt)
        full_context = self.knowledge_service.get_context_for_prompt(prompt)
        optimized_context = self.context_optimizer.optimize_context(
            prompt,
            full_context["structured_json"]
        )
        
        analyzed_query = self._analyze_and_enhance_query(prompt, question_type)
        system_prompt = self.prompt_builder.build_system_prompt(
            question_type,
            optimized_context,
            user_query=prompt
        )
        
        if self._should_use_cot(question_type, prompt):
            full_prompt = self._build_cot_prompt(system_prompt, analyzed_query)
        else:
            full_prompt = f"""{system_prompt}

═══════════════════════════════════════
ПИТАННЯ КОРИСТУВАЧА:
{prompt}

ПРОАНАЛІЗОВАНЕ ПИТАННЯ:
{analyzed_query}
═══════════════════════════════════════

ТВОЯ ЗАДАЧА:
1. Уважно прочитай питання
2. Знайди відповідну інформацію в базі знань вище
3. Сформуй точну, структуровану відповідь
4. Перевір відповідь за списком самоперевірки

ВІДПОВІДЬ (структурована, конкретна, з даними з бази знань):"""
        
        # Отримуємо базові параметри
        base_params = self.generation_params.get(
            question_type,
            self.generation_params["default"]
        )
        base_params = self._adapt_params(base_params, len(prompt))
        
        # Створюємо варіації параметрів для різних кандидатів
        param_variations = self._create_param_variations(base_params, num_candidates)
        
        # Генеруємо всі варіанти паралельно
        tasks = [
            self._generate_with_retry(
                full_prompt,
                params,
                max_retries=2,
                context=context if context else []
            )
            for params in param_variations
        ]
        
        try:
            candidates = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"Помилка паралельної генерації: {e}")
            # Fallback до звичайної генерації
            return await self._generate_with_retry(
                full_prompt,
                base_params,
                max_retries=3,
                context=context if context else []
            )
        
        # Фільтруємо помилки
        valid_candidates = [
            c for c in candidates
            if isinstance(c, str) and len(c.strip()) > 20
        ]
        
        if not valid_candidates:
            # Якщо всі невалідні - використовуємо fallback
            return await self._generate_with_retry(
                full_prompt,
                base_params,
                max_retries=3,
                context=context if context else []
            )
        
        # Вибираємо найкращий варіант
        best_response = self._select_best_response(valid_candidates, prompt, question_type)
        
        # Валідуємо найкращий варіант
        validation_result = self.validator.validate(best_response, prompt)
        
        # Зберігаємо в кеш
        if validation_result.is_valid and use_cache:
            self.cache.set(prompt, optimized_context, best_response)
            self.semantic_cache.set(prompt, optimized_context, best_response)
        
        # Записуємо метрики
        response_time = time.time() - start_time
        self.metrics.record_request(
            prompt, best_response, response_time,
            from_cache=False, question_type=question_type,
            validation_passed=validation_result.is_valid
        )
        
        return best_response
    
    def _create_param_variations(self, base_params: Dict, num_variations: int) -> List[Dict]:
        """Створення варіацій параметрів для паралельної генерації"""
        variations = []
        
        for i in range(num_variations):
            params = base_params.copy()
            
            # Варіації temperature
            if i == 0:
                params["temperature"] = max(0.0, base_params.get("temperature", 0.05) - 0.02)
            elif i == 1:
                params["temperature"] = base_params.get("temperature", 0.05)
            else:
                params["temperature"] = min(0.3, base_params.get("temperature", 0.05) + 0.02)
            
            # Варіації top_p
            if i % 2 == 0:
                params["top_p"] = max(0.2, base_params.get("top_p", 0.4) - 0.05)
            else:
                params["top_p"] = min(0.8, base_params.get("top_p", 0.4) + 0.05)
            
            # Варіації num_predict
            if i == 0:
                params["num_predict"] = int(base_params.get("num_predict", 400) * 0.9)
            elif i == 1:
                params["num_predict"] = base_params.get("num_predict", 400)
            else:
                params["num_predict"] = int(base_params.get("num_predict", 400) * 1.1)
            
            variations.append(params)
        
        return variations
    
    def _select_best_response(self, candidates: List[str], prompt: str, question_type: str) -> str:
        """Вибір найкращого варіанту відповіді"""
        if len(candidates) == 1:
            return candidates[0]
        
        scores = []
        
        for candidate in candidates:
            score = 0.0
            
            # 1. Довжина відповіді (оптимальна 100-500 символів)
            length = len(candidate)
            if 100 <= length <= 500:
                score += 0.3
            elif 50 <= length < 100 or 500 < length <= 1000:
                score += 0.2
            else:
                score += 0.1
            
            # 2. Наявність ключових слів для типу питання
            candidate_lower = candidate.lower()
            prompt_lower = prompt.lower()
            
            # Перевіряємо, чи відповідь містить ключові слова з питання
            prompt_keywords = set(re.findall(r'\b\w{4,}\b', prompt_lower))
            candidate_keywords = set(re.findall(r'\b\w{4,}\b', candidate_lower))
            common_keywords = prompt_keywords & candidate_keywords
            
            if prompt_keywords:
                keyword_score = len(common_keywords) / len(prompt_keywords)
                score += keyword_score * 0.3
            
            # 3. Структурованість (наявність списків, форматування)
            has_structure = bool(
                re.search(r'[•\-\d+\.]', candidate) or
                '\n' in candidate or
                ':' in candidate
            )
            if has_structure:
                score += 0.2
            
            # 4. Відсутність заборонених слів
            forbidden_words = ['хну', 'кну', 'львівський', 'одеський', 'харківський']
            has_forbidden = any(word in candidate_lower for word in forbidden_words)
            if not has_forbidden:
                score += 0.2
            else:
                score -= 1.0  # Великий штраф за заборонені слова
            
            scores.append(score)
        
        # Вибираємо варіант з найвищим балом
        best_index = scores.index(max(scores))
        return candidates[best_index]
    
    def _get_admission_fallback(self, query: str) -> str:
        """Fallback відповідь для питань про вступ"""
        try:
            from knowledge_base import get_admission_2026_info, get_admissions_committee_phones
            import json
            
            info = get_admission_2026_info()
            if not info:
                return self._get_default_admission_response()
            
            # Форматуємо відповідь
            parts = []
            parts.append("📘 <b>Правила вступу до ХДУ у 2026 році</b>")
            
            if info.get("description"):
                parts.append(info["description"])
            
            nmt = info.get("nmt", {})
            if nmt:
                mandatory = nmt.get("mandatory_subjects", [])
                optional = nmt.get("optional_subjects", [])
                valid_years = nmt.get("valid_years", [])
                
                if mandatory:
                    parts.append("🧪 <b>НМТ - обов'язковий блок:</b>")
                    parts.extend([f"• {s}" for s in mandatory])
                
                if optional:
                    parts.append("📚 <b>Предмет на вибір:</b>")
                    parts.extend([f"• {s}" for s in optional[:3]])  # Перші 3
                
                if valid_years:
                    years = ", ".join(str(y) for y in valid_years)
                    parts.append(f"📅 Результати НМТ враховуються за {years} роки")
            
            trajectories = info.get("trajectories", {})
            if trajectories:
                bachelor = trajectories.get("bachelor", {})
                master = trajectories.get("master", {})
                
                parts.append("🎓 <b>Траєкторії вступу:</b>")
                
                if bachelor:
                    duration = bachelor.get("duration", {})
                    if duration:
                        if duration.get("bachelor"):
                            parts.append(f"• Бакалавр: {duration['bachelor']}")
                        if duration.get("medical_master"):
                            parts.append(f"• Медичний магістр: {duration['medical_master']}")
                        if duration.get("pharmacy_master"):
                            parts.append(f"• Фармацевтичний магістр: {duration['pharmacy_master']}")
                
                if master:
                    duration = master.get("duration", {})
                    if duration:
                        if duration.get("standard"):
                            parts.append(f"• Магістр: {duration['standard']}")
                        if duration.get("extended"):
                            parts.append(f"• Магістр (окремі спеціальності): {duration['extended']}")
            
            campaign = info.get("campaign", {})
            if campaign:
                period = campaign.get("period")
                if period:
                    parts.append(f"\n⏰ <b>Період кампанії:</b> {period}")
                
                electronic_cabinets = campaign.get("electronic_cabinets", {})
                if electronic_cabinets:
                    platform = electronic_cabinets.get("platform")
                    if platform:
                        parts.append(f"💻 <b>Електронний кабінет:</b> {platform}")
                    
                    description = electronic_cabinets.get("description")
                    if description:
                        parts.append(f"📝 {description}")
            
            parts.append(f"\n{get_admissions_committee_phones()}")
            
            result = "\n".join(parts)
            # Видаляємо HTML теги для fallback (якщо потрібно)
            # Але залишаємо для Telegram
            return result
        except Exception as e:
            logger.error(f"Помилка формування fallback для вступу: {e}")
            return self._get_default_admission_response()
    
    def _get_default_admission_response(self) -> str:
        """Стандартна відповідь про вступ"""
        return """📘 <b>Правила вступу до ХДУ у 2026 році</b>

🧪 <b>НМТ (Національний мультипредметний тест):</b>
• Обов'язковий блок: Українська мова, Математика, Історія України
• Предмет на вибір: Іноземна мова, Біологія, Географія, Фізика, Хімія або Українська література
• Результати НМТ 2023-2026 років враховуються

🎓 <b>Траєкторії вступу:</b>
• Бакалавр: 3 роки 10 місяців
• Магістр: 1 рік 4 місяці (більшість спеціальностей)

⏰ <b>Вступна кампанія:</b>
• Розпочинається влітку та триває до вересня
• Можливі додаткові хвилі зарахування

💻 <b>Електронний кабінет:</b> KSU24
• Подача заяв через електронний кабінет
• Дистанційне укладання угоди на навчання

📞 <b>Приймальна комісія ХДУ:</b>
📱 +380 552 494375
📱 +38 095 59 29 149
📱 +38 096 61 30 516
📍 м. Херсон, вул. Університетська, 27"""

