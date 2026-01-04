"""
Допоміжний модуль для автоматичного пошуку вартості навчання
"""
import re
from knowledge_base import KNU_KNOWLEDGE, get_admissions_committee_phones


async def find_tuition_info(specialty_name: str = None, specialty_code: str = None) -> str:
    """
    Автоматично знаходить інформацію про вартість навчання для спеціальності
    
    Args:
        specialty_name: Назва спеціальності (наприклад, "Інформаційні системи та технології")
        specialty_code: Код спеціальності (наприклад, "121", "F6")
    
    Returns:
        Сформована відповідь про вартість навчання або порожній рядок, якщо не знайдено
    """
    if not specialty_name and not specialty_code:
        return ""
    
    # Нормалізуємо вхідні дані
    specialty_name_normalized = specialty_name.lower() if specialty_name else ""
    specialty_code_normalized = specialty_code.lower() if specialty_code else ""
    
    # Імпортуємо базу даних
    from database import db
    
    # Отримуємо вартість з бази даних
    # Спочатку шукаємо за кодом, якщо він є
    tuition_records = None
    if specialty_code_normalized:
        tuition_records = await db.get_tuition_price(specialty_code=specialty_code_normalized)
    
    # Якщо не знайдено за кодом, шукаємо за назвою
    if not tuition_records and specialty_name_normalized:
        tuition_records = await db.get_tuition_price(specialty_name=specialty_name_normalized)
    
    # Якщо все ще не знайдено, шукаємо за частиною назви
    if not tuition_records and specialty_name_normalized:
        # Використовуємо get_tuition_by_specialty_name для часткового пошуку
        tuition_records = await db.get_tuition_by_specialty_name(specialty_name_normalized)
    
    # Формуємо вартість для різних рівнів та форм навчання з бази даних
    bachelor_fulltime = None
    bachelor_parttime = None
    master_fulltime = None
    master_parttime = None
    
    if tuition_records:
        # Групуємо записи за рівнем освіти та формою навчання
        for record in tuition_records:
            level = record.get('education_level', '').lower()
            form = record.get('study_form', '').lower()
            price_monthly = record.get('price_monthly', '')
            price_semester = record.get('price_semester', '')
            price_year = record.get('price_year', '')
            price_total = record.get('price_total', '')
            
            # Формуємо рядок вартості з емодзі та переносами рядків
            price_lines = []
            if price_monthly:
                price_lines.append(f"💰 {price_monthly}")
            if price_semester:
                price_lines.append(f"💰 {price_semester}")
            if price_year:
                price_lines.append(f"💰 {price_year}")
            if price_total:
                price_lines.append(f"💰 {price_total}")
            
            price_text = '\n'.join(price_lines) if price_lines else None
            
            # Зберігаємо в відповідну змінну
            if level == 'бакалавр' and form == 'денна':
                bachelor_fulltime = price_text
            elif level == 'бакалавр' and form == 'заочна':
                bachelor_parttime = price_text
            elif level == 'магістр' and form == 'денна':
                master_fulltime = price_text
            elif level == 'магістр' and form == 'заочна':
                master_parttime = price_text
    
    # Перевіряємо, чи є дані в базі
    has_any_data = bachelor_fulltime or bachelor_parttime or master_fulltime or master_parttime
    
    # Якщо немає даних в базі - повертаємо повідомлення про відсутність даних
    if not has_any_data:
        # Формуємо назву спеціальності для відповіді
        if specialty_code and not specialty_name:
            specialty_display = f"спеціальність (код {specialty_code.upper()})"
        else:
            specialty_display = specialty_name.title() if specialty_name else "цієї спеціальності"
            if specialty_code:
                specialty_display += f" (код {specialty_code.upper()})"
        
        return (
            f"ℹ️ <b>Вартість навчання для {specialty_display}</b>\n\n"
            "На жаль, вартість навчання для цієї спеціальності поки не вказана в системі.\n\n"
            f"Для отримання актуальної інформації про вартість навчання звернися до приймальної комісії ХДУ:\n\n{get_admissions_committee_phones()}"
        )
    
    # Формуємо відповідь з правильною назвою спеціальності
    # Якщо є код, але немає назви - використовуємо загальну формулювання
    if specialty_code and not specialty_name:
        specialty_display = f"спеціальність (код {specialty_code.upper()})"
    else:
        # Використовуємо назву з бази даних або оригінальну назву
        if tuition_records and len(tuition_records) > 0:
            # Беремо назву з першого запису
            specialty_display = tuition_records[0].get('specialty_name', specialty_name.title() if specialty_name else "спеціальності")
            # Капіталізуємо першу літеру
            specialty_display = specialty_display[0].upper() + specialty_display[1:] if specialty_display else "спеціальності"
        else:
            specialty_display = specialty_name.title() if specialty_name else "спеціальності"
        
        if specialty_code:
            specialty_display += f" (код {specialty_code.upper()})"
    
    # Формуємо відповідь тільки з доступними даними
    response_parts = [f"Вартість навчання на {specialty_display} в ХДУ:"]
    
    if bachelor_fulltime or bachelor_parttime:
        response_parts.append("\n<b>Бакалавр:</b>")
        if bachelor_fulltime:
            response_parts.append(f"• Денна форма:\n{bachelor_fulltime}")
        if bachelor_parttime:
            response_parts.append(f"• Заочна форма:\n{bachelor_parttime}")
    
    if master_fulltime or master_parttime:
        response_parts.append("\n<b>Магістр:</b>")
        if master_fulltime:
            response_parts.append(f"• Денна форма:\n{master_fulltime}")
        if master_parttime:
            response_parts.append(f"• Заочна форма:\n{master_parttime}")
    
    response_parts.append("\n📅 Вартість вказана для 2025-2026 навчального року (1 курс).")
    response_parts.append("Для уточнення актуальної вартості звернися до приймальної комісії ХДУ:")
    response_parts.append(get_admissions_committee_phones())
    
    return "\n".join(response_parts)


def extract_specialty_from_message(message: str) -> tuple:
    """
    Витягує назву спеціальності та код з повідомлення користувача
    
    Args:
        message: Повідомлення користувача
    
    Returns:
        Tuple (specialty_name, specialty_code) або (None, None)
    """
    message_lower = message.lower()
    
    # Шукаємо коди спеціальностей (розширений список паттернів)
    # ВАЖЛИВО: Порядок має значення - спочатку більш конкретні, потім загальні
    code_patterns = [
        # Коди з галузями (найбільш конкретні): A4.11, B2.3, А4.11 (кирилиця) тощо
        (r'\b([a-z]\d+\.\d+)\b', None),  # "A4.11", "B2.3", "F6.1" (латиниця)
        (r'\b([а-я]\d+\.\d+)\b', None),  # "А4.11", "Б2.3", "Ф6.1" (кирилиця)
        # Конкретні коди з літерами (точний збіг) - відомі коди
        (r'\bf6\b', 'F6'),
        (r'\bf2\b', 'F2'),
        (r'\bf3\b', 'F3'),
        # Числові коди (точний збіг) - відомі коди
        (r'\b121\b', '121'),
        # Коди з контекстом (конкретні)
        (r'код\s+(\d{3})', None),  # "код 121", "код 123" (будь-який 3-значний)
        (r'код\s+([a-z]\d+)', None),  # "код F6", "код A1" (будь-який код з літерою)
        (r'код\s+([a-z]\d+\.\d+)', None),  # "код A4.11", "код B2.3" (латиниця)
        (r'код\s+([а-я]\d+\.\d+)', None),  # "код А4.11", "код Б2.3" (кирилиця)
        (r'спеціальність\s+(\d{3})', None),  # "спеціальність 121", "спеціальність 123"
        (r'спеціальність\s+([a-z]\d+)', None),  # "спеціальність F6", "спеціальність A1"
        (r'спеціальність\s+([a-z]\d+\.\d+)', None),  # "спеціальність A4.11" (латиниця)
        (r'спеціальність\s+([а-я]\d+\.\d+)', None),  # "спеціальність А4.11" (кирилиця)
        (r'на\s+(\d{3})', None),  # "на 121", "а на 123" (будь-який 3-значний)
        (r'на\s+([a-z]\d+)', None),  # "на F6", "а на A1" (будь-який код з літерою)
        (r'на\s+([a-z]\d+\.\d+)', None),  # "на A4.11", "а на B2.3" (латиниця)
        (r'на\s+([а-я]\d+\.\d+)', None),  # "на А4.11", "а на Б2.3" (кирилиця)
        (r'по\s+(\d{3})', None),  # "по 121", "по 123"
        (r'по\s+([a-z]\d+)', None),  # "по F6", "по A1"
        (r'по\s+([a-z]\d+\.\d+)', None),  # "по A4.11" (латиниця)
        (r'по\s+([а-я]\d+\.\d+)', None),  # "по А4.11" (кирилиця)
        # Загальні паттерни для будь-яких кодів (в кінці списку)
        (r'вартість.*?(\d{3})', None),  # "вартість 121", "вартість 123" (будь-який 3-значний)
        (r'вартість.*?([a-z]\d+\.\d+)', None),  # "вартість A4.11" (латиниця)
        (r'вартість.*?([а-я]\d+\.\d+)', None),  # "вартість А4.11" (кирилиця)
        (r'ціна.*?(\d{3})', None),  # "ціна 121", "ціна 123"
        (r'ціна.*?([a-z]\d+\.\d+)', None),  # "ціна A4.11" (латиниця)
        (r'коштує.*?(\d{3})', None),  # "коштує 121", "коштує 123"
        (r'коштує.*?([a-z]\d+\.\d+)', None),  # "коштує A4.11" (латиниця)
        # Загальний паттерн для будь-якого 3-значного коду (якщо не знайдено іншого)
        (r'\b(\d{3})\b', None),  # "121", "123", "456" (будь-який 3-значний код)
        # Загальний паттерн для кодів з літерами (якщо не знайдено іншого)
        (r'\b([a-z]\d+)\b', None),  # "F6", "A1", "B2" (будь-який код з літерою, латиниця)
        (r'\b([а-я]\d+)\b', None),  # "А4", "Б2", "Ф6" (будь-який код з літерою, кирилиця)
    ]
    
    specialty_code = None
    for pattern, code in code_patterns:
        match = re.search(pattern, message_lower, re.IGNORECASE)
        if match:
            if code:
                specialty_code = code
            else:
                extracted_code = match.group(1)
                # Перевіряємо, чи це дійсно код спеціальності (не рік, не телефон тощо)
                # 3-значні коди: 100-999 (але виключаємо очевидні не-коди)
                if extracted_code.isdigit():
                    code_num = int(extracted_code)
                    # Виключаємо роки (2020-2029, 2030-2039 тощо) та інші очевидні не-коди
                    if 100 <= code_num <= 999 and not (2000 <= code_num <= 2099):
                        specialty_code = extracted_code
                else:
                    # Коди з літерами або з галузями: нормалізуємо (великі літери)
                    # Конвертуємо кирилицю в латиницю для уніфікації (А -> A, Б -> B тощо)
                    cyrillic_to_latin = {
                        'а': 'A', 'б': 'B', 'в': 'V', 'г': 'G', 'д': 'D', 'е': 'E', 'є': 'E',
                        'ж': 'Zh', 'з': 'Z', 'и': 'I', 'і': 'I', 'ї': 'I', 'й': 'Y', 'к': 'K',
                        'л': 'L', 'м': 'M', 'н': 'N', 'о': 'O', 'п': 'P', 'р': 'R', 'с': 'S',
                        'т': 'T', 'у': 'U', 'ф': 'F', 'х': 'H', 'ц': 'Ts', 'ч': 'Ch', 'ш': 'Sh',
                        'щ': 'Shch', 'ь': '', 'ю': 'Yu', 'я': 'Ya'
                    }
                    # Конвертуємо першу літеру з кирилиці в латиницю (якщо потрібно)
                    if extracted_code[0].lower() in cyrillic_to_latin:
                        first_letter = cyrillic_to_latin[extracted_code[0].lower()].upper()
                        specialty_code = first_letter + extracted_code[1:].upper()
                    else:
                        specialty_code = extracted_code.upper()
            if specialty_code:
                break
    
    # Шукаємо назви спеціальностей автоматично з knowledge_base
    specialty_name = None
    
    # Кешуємо список спеціальностей (щоб не генерувати кожного разу)
    if not hasattr(extract_specialty_from_message, '_specialty_cache'):
        from knowledge_base import FACULTY_SPECIALTIES, get_faculty_specialties_list
        all_specialties = []
        for faculty_id in FACULTY_SPECIALTIES.keys():
            specialties = get_faculty_specialties_list(faculty_id)
            for spec in specialties:
                base_name = spec.split('(')[0].strip()
                if base_name:
                    all_specialties.append(base_name)
        
        # Сортуємо від довгих до коротких (для точнішого пошуку)
        extract_specialty_from_message._specialty_cache = sorted(
            set(all_specialties), 
            key=len, 
            reverse=True
        )
    
    specialties = extract_specialty_from_message._specialty_cache
    
    # 1. Спочатку шукаємо точне співпадіння (повна назва)
    for specialty in specialties:
        spec_lower = specialty.lower()
        # Перевіряємо чи містить повідомлення назву спеціальності
        if spec_lower in message_lower:
            specialty_name = specialty
            break
        
        # Перевіряємо чи повідомлення міститься в назві (для коротких запитів)
        if message_lower in spec_lower and len(message_lower) >= 5:
            specialty_name = specialty
            break
    
    # 2. Якщо не знайдено - шукаємо за значущими словами (найшвидший спосіб)
    if not specialty_name:
        # Словник загальних слів, які не повинні використовуватись для пошуку
        stop_words = {'освіта', 'спеціальність', 'спеціальна', 'середня', 'та', 'і', 'з', 
                     'для', 'про', 'на', 'в', 'до', 'різні', 'спеціалізації', 'рік', 'років'}
        
        # Вираховуємо слова з повідомлення один раз (оптимізація)
        message_words = set(w for w in re.findall(r'\b\w+\b', message_lower) 
                           if len(w) >= 4 and w not in stop_words)
        
        for specialty in specialties:
            spec_lower = specialty.lower()
            spec_words = [w for w in re.findall(r'\b\w+\b', spec_lower) 
                         if len(w) >= 4 and w not in stop_words]
            
            if spec_words:
                # Швидка перевірка через set intersection
                matching_words = set(spec_words) & message_words
                if len(matching_words) >= min(2, len(spec_words)):  # Мінімум 2 слова або всі якщо менше
                    specialty_name = specialty
                    break
    
    # 3. Якщо все ще не знайдено - шукаємо часткові збіги (хоча б одне значуще слово)
    if not specialty_name:
        # Використовуємо вже обчислені слова з повідомлення
        for specialty in specialties:
            spec_lower = specialty.lower()
            spec_words = [w for w in re.findall(r'\b\w+\b', spec_lower) 
                         if len(w) >= 5]  # Тільки довгі слова
            
            # Швидка перевірка через set
            spec_words_set = set(spec_words)
            if spec_words_set & message_words:  # Якщо є хоча б одне співпадіння
                specialty_name = specialty
                break
    
    return (specialty_name, specialty_code)

