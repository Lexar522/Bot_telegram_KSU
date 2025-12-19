"""
Сервіс для роботи з єдиною базою знань
"""
import re
from knowledge_base import (
    KNU_KNOWLEDGE,
    KNOWLEDGE_BASE,
    get_knu_context,
    get_structured_context,
    get_admission_2026_context,
)


class KnowledgeService:
    """Сервіс для роботи з базою знань про ХДУ"""
    
    def get_knowledge_base(self) -> str:
        """
        Отримує повну базу знань про ХДУ (текст + структурований JSON)
        
        Returns:
            str: База знань у форматі тексту
        """
        # Об'єднуємо текстовий опис та структурований JSON,
        # щоб LLM мала і читабельний контент, і точні поля для фактів
        structured = get_structured_context()
        return f"{get_knu_context()}\n\n=== СТРУКТУРОВАНІ ДАНІ (JSON) ===\n{structured}"
    
    def get_structured_knowledge(self) -> str:
        """
        Отримує структуровану базу знань
        
        Returns:
            str: Структурована база знань
        """
        return get_structured_context()

    def get_admission_2026_context(self) -> str:
        """Отримує контекст лише про вступ 2026 (JSON)"""
        return get_admission_2026_context()

    def get_context_for_prompt(self, query: str) -> dict:
        """
        Повертає максимально релевантний контекст для промпту (звужений),
        щоб LLM працювала лише з потрібними даними.
        """
        ql = (query or "").lower()

        admission_keywords = [
            "вступ", "вступ 2026", "вступна кампанія", "вступна кампанія 2026",
            "правила вступу", "порядок вступу", "правила прийому", "правила прийому 2026",
            "кампанія 2026", "кампанії 2026", "дата вступу", "дати вступу",
            "коли починається вступ", "коли розпочинається вступ", "коли стартує вступ",
            "коли починається вступна кампанія", "коли розпочинається вступна кампанія",
            "коли стартує вступна кампанія", "початок вступної кампанії", "старт вступної кампанії",
            "електронний кабінет", "електронні кабінети", "ksu24", "ксу24",
            "заява", "заяви", "подача заяв", "подання заяв", "дедлайн", "термін подачі",
            "хвиля", "хвилі", "друга хвиля", "додаткова хвиля",
            "траєкторії", "траєкторія", "траєкторії вступу", "нмт", "національний мультипредметний тест",
        ]
        docs_keywords = [
            "документ", "документи", "список документів", "перелік документів",
            "потрібні документи", "які документи", "що потрібно подати", "пакет документів",
            "подати документи", "подача документів",
        ]
        faculties_keywords = [
            "факультет", "факультети", "спеціальності", "спеціальність", "напрям", "напрями",
            "освітні програми", "бакалавр", "магістр", "кафедра", "кафедри",
        ]
        contacts_keywords = [
            "контакт", "контакти", "адрес", "телефон", "приймальн", "email", "пошта", "сайт", "web", "вебсайт",
        ]
        tuition_keywords = [
            "вартість", "вартість навчання", "ціна", "скільки коштує", "оплата", "коштує навчання", "тарифи",
            "контракт", "контрактна вартість", "скільки платити", "ціна навчання", "оплата за семестр",
            "оплата за рік", "оплата за місяць", "скільки коштує навчання",
        ]

        is_admission = any(kw in ql for kw in admission_keywords)
        is_docs = any(kw in ql for kw in docs_keywords)
        is_faculties = any(kw in ql for kw in faculties_keywords)
        is_contacts = any(kw in ql for kw in contacts_keywords)
        is_tuition = any(kw in ql for kw in tuition_keywords)

        sections = {}
        matched = []

        # admission 2026 block
        if is_admission and "admission" in KNOWLEDGE_BASE:
            sections["admission_2026"] = KNOWLEDGE_BASE["admission"].get("year_2026", {})
            matched.append("admission")

        # tuition block
        if is_tuition and "tuition" in KNOWLEDGE_BASE:
            sections["tuition"] = KNOWLEDGE_BASE["tuition"]
            matched.append("tuition")

        # faculties block
        if is_faculties:
            sections["faculties"] = KNOWLEDGE_BASE.get("faculties", {})
            sections["fields"] = KNOWLEDGE_BASE.get("fields", {})
            matched.append("faculties")

        # documents
        if is_docs and "documents" in KNOWLEDGE_BASE:
            sections["documents"] = KNOWLEDGE_BASE["documents"]
            matched.append("documents")

        # contacts
        if is_contacts:
            sections["contacts"] = KNOWLEDGE_BASE.get("contacts", {})
            matched.append("contacts")

        # If nothing matched, give minimal core info + contacts
        if not sections:
            sections["core"] = {
                "university": KNOWLEDGE_BASE.get("university", {}),
                "contacts": KNOWLEDGE_BASE.get("contacts", {}),
            }

        # Build text + structured JSON
        structured = sections
        structured["_markers"] = {
            "matched": matched,
            "admission_keywords": admission_keywords,
            "docs_keywords": docs_keywords,
            "faculties_keywords": faculties_keywords,
            "contacts_keywords": contacts_keywords,
            "tuition_keywords": tuition_keywords,
        }
        text = KNU_KNOWLEDGE  # текстова частина (повна), щоб не втратити опис

        return {
            "text": text,
            "structured_json": structured,
        }
    
    def get_knowledge_dict(self) -> dict:
        """
        Отримує структуровану базу знань як словник
        
        Returns:
            dict: Структурована база знань
        """
        return KNOWLEDGE_BASE
    
    def search_in_knowledge(self, query: str) -> str:
        """
        Шукає інформацію в базі знань (спрощена версія)
        
        Args:
            query: Запит для пошуку
            
        Returns:
            str: Знайдена інформація або повна база знань
        """
        # Для простоти повертаємо всю базу знань
        # В майбутньому можна додати семантичний пошук
        return self.get_knowledge_base()

