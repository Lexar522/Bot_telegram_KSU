"""
Варіанти автоматичного витягування спеціальностей без жорстко закодованого списку
"""

import re
from typing import List, Tuple, Set
from knowledge_base import FACULTY_SPECIALTIES, get_faculty_specialties_list, get_faculties_list


# ============================================================================
# ВАРІАНТ 1: Автоматичне витягування з knowledge_base + генерація ключових слів
# ============================================================================
def generate_specialty_keywords_v1() -> List[Tuple[str, List[str]]]:
    """
    Автоматично генерує список спеціальностей та ключових слів з knowledge_base
    """
    specialty_keywords = []
    
    # Отримуємо всі спеціальності з усіх факультетів
    all_specialties = set()
    for faculty_id in FACULTY_SPECIALTIES.keys():
        specialties = get_faculty_specialties_list(faculty_id)
        for spec in specialties:
            # Прибираємо додаткову інформацію в дужках
            base_name = spec.split('(')[0].strip()
            if base_name:
                all_specialties.add(base_name)
    
    # Генеруємо ключові слова для кожної спеціальності
    for specialty_name in sorted(all_specialties, key=len, reverse=True):  # Сортуємо від довгих до коротких
        keywords = generate_keywords_from_name(specialty_name)
        specialty_keywords.append((specialty_name, keywords))
    
    return specialty_keywords


def generate_keywords_from_name(specialty_name: str) -> List[str]:
    """
    Автоматично генерує ключові слова з назви спеціальності
    """
    keywords = []
    name_lower = specialty_name.lower()
    
    # Додаємо повну назву
    keywords.append(name_lower)
    
    # Розбиваємо на слова
    words = re.findall(r'\b\w+\b', name_lower)
    
    # Виключаємо загальні слова
    stop_words = {'та', 'і', 'з', 'для', 'про', 'на', 'в', 'до', 'освіта', 'спеціальність', 
                  'спеціальна', 'середня', 'різні', 'спеціалізації', 'рік', 'років', 'роки'}
    
    # Додаємо окремі значущі слова
    for word in words:
        if word not in stop_words and len(word) >= 4:
            keywords.append(word)
    
    # Додаємо варіанти з суфіксами (для професій)
    profession_suffixes = {
        'ологія': ['олог', 'ологічний'],
        'іка': ['ік', 'ічний'],
        'ія': ['ій', 'ійський'],
        'ство': ['ств', 'ствний'],
    }
    
    for suffix, variants in profession_suffixes.items():
        if name_lower.endswith(suffix):
            base = name_lower[:-len(suffix)]
            for variant in variants:
                keywords.append(base + variant)
    
    # Додаємо скорочення для довгих назв
    if len(words) > 2:
        # Перші літери слів
        abbreviation = ''.join([w[0] for w in words[:3] if len(w) >= 4])
        if abbreviation and len(abbreviation) >= 2:
            keywords.append(abbreviation)
    
    return list(set(keywords))  # Прибираємо дублікати


# ============================================================================
# ВАРІАНТ 2: Комбінування з базою даних + knowledge_base
# ============================================================================
async def generate_specialty_keywords_v2() -> List[Tuple[str, List[str]]]:
    """
    Комбінує дані з бази даних та knowledge_base для максимальної точності
    """
    specialty_keywords = []
    
    # 1. Отримуємо спеціальності з бази даних (якщо доступна)
    db_specialties = set()
    try:
        from database import db
        all_tuition = await db.get_all_tuition_prices()
        for tuition in all_tuition:
            spec_name = tuition.get('specialty_name', '').strip()
            if spec_name:
                base_name = spec_name.split('(')[0].strip()
                db_specialties.add(base_name)
    except:
        pass
    
    # 2. Отримуємо спеціальності з knowledge_base
    kb_specialties = set()
    for faculty_id in FACULTY_SPECIALTIES.keys():
        specialties = get_faculty_specialties_list(faculty_id)
        for spec in specialties:
            base_name = spec.split('(')[0].strip()
            if base_name:
                kb_specialties.add(base_name)
    
    # 3. Об'єднуємо обидва джерела
    all_specialties = db_specialties.union(kb_specialties)
    
    # 4. Генеруємо ключові слова
    for specialty_name in sorted(all_specialties, key=len, reverse=True):
        keywords = generate_keywords_from_name(specialty_name)
        specialty_keywords.append((specialty_name, keywords))
    
    return specialty_keywords


# ============================================================================
# ВАРІАНТ 3: Fuzzy matching з автоматичним пошуком
# ============================================================================
def extract_specialty_fuzzy(message: str, specialty_list: List[str]) -> Tuple[str, float]:
    """
    Знаходить найбільш схожу спеціальність за допомогою fuzzy matching
    Повертає (назва_спеціальності, коефіцієнт_схожості)
    """
    message_lower = message.lower()
    best_match = None
    best_score = 0.0
    
    for specialty in specialty_list:
        spec_lower = specialty.lower()
        
        # Точне співпадіння
        if spec_lower in message_lower or message_lower in spec_lower:
            return (specialty, 1.0)
        
        # Перевірка окремих слів
        spec_words = set(re.findall(r'\b\w+\b', spec_lower))
        msg_words = set(re.findall(r'\b\w+\b', message_lower))
        
        # Виключаємо загальні слова
        stop_words = {'та', 'і', 'з', 'для', 'про', 'на', 'в', 'до', 'освіта', 
                      'спеціальність', 'спеціальна', 'середня'}
        spec_words = spec_words - stop_words
        msg_words = msg_words - stop_words
        
        # Рахуємо співпадіння
        common_words = spec_words.intersection(msg_words)
        if common_words:
            score = len(common_words) / max(len(spec_words), len(msg_words))
            if score > best_score:
                best_score = score
                best_match = specialty
    
    return (best_match, best_score) if best_match and best_score > 0.3 else (None, 0.0)


async def extract_specialty_auto_v3(message: str) -> Tuple[str, str]:
    """
    Автоматичне витягування спеціальності без жорстко закодованого списку
    Використовує fuzzy matching
    """
    message_lower = message.lower()
    
    # Збираємо всі спеціальності
    all_specialties = []
    for faculty_id in FACULTY_SPECIALTIES.keys():
        specialties = get_faculty_specialties_list(faculty_id)
        all_specialties.extend(specialties)
    
    # Шукаємо найбільш схожу
    specialty_name, score = extract_specialty_fuzzy(message_lower, all_specialties)
    
    # Також шукаємо код (як і раніше)
    specialty_code = extract_code_from_message(message)
    
    return (specialty_name, specialty_code)


def extract_code_from_message(message: str) -> str:
    """Витягує код спеціальності (логіка залишається та сама)"""
    # Тут можна використати існуючу логіку з extract_specialty_from_message
    # Для простоти залишаю заглушку
    return None


# ============================================================================
# ВАРІАНТ 4: Гібридний підхід (рекомендований)
# ============================================================================
async def extract_specialty_auto_hybrid(message: str) -> Tuple[str, str]:
    """
    Гібридний підхід: комбінує автоматичне витягування з кешуванням
    """
    message_lower = message.lower()
    
    # Кешуємо список спеціальностей (щоб не генерувати кожного разу)
    if not hasattr(extract_specialty_auto_hybrid, '_specialty_cache'):
        all_specialties = []
        for faculty_id in FACULTY_SPECIALTIES.keys():
            specialties = get_faculty_specialties_list(faculty_id)
            for spec in specialties:
                base_name = spec.split('(')[0].strip()
                if base_name:
                    all_specialties.append(base_name)
        
        # Сортуємо від довгих до коротких (для точнішого пошуку)
        extract_specialty_auto_hybrid._specialty_cache = sorted(
            set(all_specialties), 
            key=len, 
            reverse=True
        )
    
    specialties = extract_specialty_auto_hybrid._specialty_cache
    
    # 1. Спочатку шукаємо точне співпадіння
    for specialty in specialties:
        spec_lower = specialty.lower()
        # Перевіряємо чи містить повідомлення назву спеціальності
        if spec_lower in message_lower:
            return (specialty, None)
        
        # Перевіряємо окремі значущі слова
        spec_words = [w for w in re.findall(r'\b\w+\b', spec_lower) 
                     if len(w) >= 4 and w not in {'освіта', 'спеціальність', 'спеціальна', 'середня'}]
        
        if spec_words and all(word in message_lower for word in spec_words[:2]):  # Перші 2 слова
            return (specialty, None)
    
    # 2. Якщо не знайдено - використовуємо fuzzy matching
    specialty_name, score = extract_specialty_fuzzy(message_lower, specialties)
    if specialty_name and score > 0.4:
        return (specialty_name, None)
    
    # 3. Шукаємо код (як і раніше)
    specialty_code = extract_code_from_message(message)
    
    return (None, specialty_code)

