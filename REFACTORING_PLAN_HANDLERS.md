# 📋 План рефакторингу handlers.py

## 🎯 Мета
Розбити великий файл `handlers.py` (1610 рядків) на логічні модулі для покращення підтримуваності, тестованості та читабельності коду.

---

## 📊 Поточний стан

### Статистика:
- **Розмір файлу:** 1610 рядків
- **Кількість функцій:** ~25+ обробників
- **Залежності:** багато імпортів, спільні утиліти

### Основні компоненти:
1. **Команди** (`/start`, `/help`, `/stats`, `/history`, `/contacts`)
2. **Обробка меню** (кнопки головного меню)
3. **Чат з AI** (основний обробник повідомлень - ~900 рядків)
4. **Нагадування** (створення, перегляд, управління)
5. **Налаштування** (спеціалізація, нагадування)
6. **Callback queries** (факультети, звіти про помилки)
7. **Утиліти** (форматування, перевірки, допоміжні функції)

---

## 🏗️ Нова структура

```
handlers/
├── __init__.py              # Експорт головного router
├── commands.py              # Команди бота (/start, /help, /stats, /history, /contacts)
├── menu_handlers.py         # Обробка кнопок головного меню
├── chat_handler.py         # Основний чат з AI (найбільший модуль)
├── reminders.py            # Нагадування (створення, перегляд, FSM)
├── settings.py             # Налаштування (спеціалізація, нагадування)
├── callbacks.py            # Callback queries (факультети, звіти)
├── utils.py                # Допоміжні функції (форматування, перевірки)
└── states.py               # FSM стани
```

---

## 📝 Детальний план виконання

### **Етап 1: Підготовка** ⏱️ 30 хвилин

#### 1.1. Створення структури директорій
```bash
mkdir handlers
touch handlers/__init__.py
touch handlers/commands.py
touch handlers/menu_handlers.py
touch handlers/chat_handler.py
touch handlers/reminders.py
touch handlers/settings.py
touch handlers/callbacks.py
touch handlers/utils.py
touch handlers/states.py
```

#### 1.2. Створення спільних імпортів
В `handlers/__init__.py`:
```python
"""
Модуль обробників Telegram-бота
"""
from aiogram import Router
from handlers.commands import router as commands_router
from handlers.menu_handlers import router as menu_router
from handlers.chat_handler import router as chat_router
from handlers.reminders import router as reminders_router
from handlers.settings import router as settings_router
from handlers.callbacks import router as callbacks_router

# Головний router, який об'єднує всі під-роутери
main_router = Router()

# Підключення всіх роутерів
main_router.include_router(commands_router)
main_router.include_router(menu_router)
main_router.include_router(chat_router)
main_router.include_router(reminders_router)
main_router.include_router(settings_router)
main_router.include_router(callbacks_router)

# Для зворотної сумісності
router = main_router
```

---

### **Етап 2: Винесення утиліт** ⏱️ 1 година

#### 2.1. Створення `handlers/utils.py`
**Функції для перенесення:**
- `_agent_log()` - логування для debug
- `_format_admission_2026()` - форматування інформації про вступ
- `_check_and_fix_forbidden_universities()` - перевірка заборонених університетів
- `_convert_markdown_to_html()` - конвертація markdown в HTML
- `detect_faculty_by_keywords()` - визначення факультету за ключовими словами

**Структура:**
```python
"""
Допоміжні функції для обробників
"""
import os
import json
import time
import re
from pathlib import Path
from typing import Optional

# Константи
DEBUG_LOG_PATH = os.getenv(
    "DEBUG_LOG_PATH",
    str(Path(__file__).parent.parent / ".cursor" / "debug.log")
)

def agent_log(hypothesis_id: str, location: str, message: str, data: dict):
    """Логування для debug"""
    ...

def format_admission_2026(info: dict) -> str:
    """Форматує структуровану інформацію про вступ 2026"""
    ...

def check_and_fix_forbidden_universities(response: str, user_message: str) -> str:
    """Перевіряє відповідь на заборонені університети"""
    ...

def convert_markdown_to_html(text: str) -> str:
    """Конвертує markdown форматування в HTML"""
    ...

def detect_faculty_by_keywords(text: str) -> Optional[str]:
    """Визначає факультет за ключовими словами"""
    ...
```

---

### **Етап 3: Винесення FSM станів** ⏱️ 15 хвилин

#### 3.1. Створення `handlers/states.py`
```python
"""
FSM стани для обробників
"""
from aiogram.fsm.state import State, StatesGroup

class ReminderStates(StatesGroup):
    """Стани для створення нагадувань"""
    waiting_for_name = State()
    waiting_for_date = State()
```

---

### **Етап 4: Команди** ⏱️ 1 година

#### 4.1. Створення `handlers/commands.py`
**Функції для перенесення:**
- `cmd_start()` - `/start`
- `cmd_help()` - `/help`
- `cmd_contacts()` - `/contacts`
- `cmd_stats()` - `/stats`
- `cmd_history()` - `/history`

**Структура:**
```python
"""
Обробка команд бота
"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command, CommandStart
from database import db
from keyboards import get_main_menu
from knowledge_base import get_knu_contacts

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обробка команди /start"""
    ...

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обробка команди /help"""
    ...

@router.message(Command("contacts"))
async def cmd_contacts(message: Message):
    """Обробка команди /contacts"""
    ...

@router.message(Command("stats"))
@router.message(F.text.in_(["📊 Статистика", "/stats"]))
async def cmd_stats(message: Message):
    """Статистика користувача"""
    ...

@router.message(Command("history"))
@router.message(F.text.in_(["📜 Історія", "/history"]))
async def cmd_history(message: Message):
    """Історія діалогів"""
    ...
```

---

### **Етап 5: Обробка меню** ⏱️ 1.5 години

#### 5.1. Створення `handlers/menu_handlers.py`
**Функції для перенесення:**
- `get_advice_handler()` - "📚 Поради"
- `get_documents_handler()` - "📄 Документи"
- `get_reminders_handler()` - "⏰ Нагадування"
- `contacts_handler()` - "📞 Контакти"
- `ask_question_handler()` - "💬 Задати питання"
- `settings_handler()` - "⚙️ Налаштування"
- `back_handler()` - "⬅️ Назад"
- `main_menu_handler()` - "🏠 Головне меню"

**Структура:**
```python
"""
Обробка кнопок головного меню
"""
from aiogram import Router, F
from aiogram.types import Message
from database import db
from keyboards import (
    get_main_menu, get_back_keyboard,
    get_reminders_management_keyboard
)
from knowledge_base import get_knu_contacts, get_documents_text
from handlers.utils import convert_markdown_to_html

router = Router()

@router.message(F.text.in_(["📚 Поради", "📚 Поради щодо вступу"]))
async def get_advice_handler(message: Message):
    """Обробка запиту на поради"""
    ...

@router.message(F.text.in_(["📄 Документи", "📄 Список документів"]))
async def get_documents_handler(message: Message):
    """Обробка запиту на список документів"""
    ...

# ... інші обробники
```

---

### **Етап 6: Налаштування** ⏱️ 1 година

#### 6.1. Створення `handlers/settings.py`
**Функції для перенесення:**
- `settings_handler()` - "⚙️ Налаштування"
- `change_specialization_handler()` - "🎯 Спеціалізація"
- `set_specialization_handler()` - встановлення спеціалізації
- `toggle_reminders_handler()` - "🔔 Нагадування"

**Структура:**
```python
"""
Обробка налаштувань
"""
from aiogram import Router, F
from aiogram.types import Message
from database import db
from keyboards import (
    get_main_menu, get_settings_keyboard,
    get_specializations_keyboard
)

router = Router()

@router.message(F.text == "⚙️ Налаштування")
async def settings_handler(message: Message):
    """Обробка налаштувань"""
    ...

@router.message(F.text.in_(["🎯 Спеціалізація", "🎯 Змінити спеціалізацію"]))
async def change_specialization_handler(message: Message):
    """Обробка зміни спеціалізації"""
    ...

# ... інші обробники
```

---

### **Етап 7: Нагадування** ⏱️ 1.5 години

#### 7.1. Створення `handlers/reminders.py`
**Функції для перенесення:**
- `get_reminders_handler()` - перегляд нагадувань
- `create_reminder_start()` - початок створення
- `process_reminder_name()` - обробка назви
- `process_reminder_date()` - обробка дати
- `list_reminders_handler()` - список нагадувань

**Структура:**
```python
"""
Обробка нагадувань
"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from datetime import datetime
from database import db
from keyboards import (
    get_main_menu, get_back_keyboard,
    get_reminders_management_keyboard
)
from handlers.states import ReminderStates

router = Router()

@router.message(F.text.in_(["⏰ Нагадування", "⏰ Мої нагадування"]))
async def get_reminders_handler(message: Message):
    """Обробка запиту на нагадування"""
    ...

@router.message(F.text.in_(["➕ Створити", "➕ Створити нагадування"]))
async def create_reminder_start(message: Message, state: FSMContext):
    """Початок створення нагадування"""
    ...

# ... інші обробники
```

---

### **Етап 8: Callback queries** ⏱️ 1 година

#### 8.1. Створення `handlers/callbacks.py`
**Функції для перенесення:**
- `faculty_handler()` - обробка вибору факультету
- `report_error_handler()` - звіт про помилку

**Структура:**
```python
"""
Обробка callback queries
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery
from datetime import datetime
import os
import logging
from database import db
from knowledge_base import get_faculty_specialties
from keyboards import get_feedback_keyboard

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data.startswith("faculty_"))
async def faculty_handler(callback: CallbackQuery):
    """Обробка вибору факультету"""
    ...

@router.callback_query(F.data.startswith("report_"))
async def report_error_handler(callback: CallbackQuery):
    """Обробка кнопки 'Повідомити про помилку'"""
    ...
```

---

### **Етап 9: Чат з AI** ⏱️ 3-4 години (найскладніший)

#### 9.1. Створення `handlers/chat_handler.py`
**Функція для перенесення:**
- `chat_handler()` - основний обробник повідомлень (~900 рядків)

**Підхід:**
Розбити велику функцію на менші допоміжні функції:
- `_process_greetings()` - обробка привітань
- `_process_document_question()` - питання про документи
- `_process_tuition_question()` - питання про вартість
- `_process_faculty_question()` - питання про факультети
- `_process_admission_question()` - питання про вступ
- `_process_law_question()` - питання про право
- `_generate_ai_response()` - генерація відповіді через AI
- `_post_process_response()` - пост-обробка відповіді

**Структура:**
```python
"""
Обробка звичайних повідомлень (чат з AI)
"""
from aiogram import Router, F
from aiogram.types import Message
from database import db
from ollama_client import ollama
from services.response_service import ResponseService
from keyboards import (
    get_main_menu, get_back_keyboard,
    get_faculties_keyboard, get_feedback_keyboard
)
from handlers.utils import (
    agent_log, convert_markdown_to_html,
    detect_faculty_by_keywords
)
from knowledge_base import (
    get_documents_text, get_faculties_list,
    get_faculty_specialties, get_admission_2026_info
)
from tuition_helper import find_tuition_info, extract_specialty_from_message

router = Router()

# Константи
MENU_BUTTONS = [
    "📚 Поради", "📄 Документи", "📞 Контакти",
    # ... інші кнопки
]

GREETINGS = ["привіт", "вітаю", "добрий день", ...]

@router.message()
async def chat_handler(message: Message):
    """Обробка звичайних повідомлень (чат з AI)"""
    user_message = message.text
    
    # Перевірка на команди та кнопки меню
    if not user_message or user_message.startswith("/"):
        return
    
    if user_message in MENU_BUTTONS:
        return
    
    # Обробка привітань
    if _is_greeting(user_message):
        return await _handle_greeting(message)
    
    # Обробка різних типів питань
    if _is_document_question(user_message):
        return await _handle_document_question(message, user_message)
    
    if _is_tuition_question(user_message):
        return await _handle_tuition_question(message, user_message)
    
    # ... інші перевірки
    
    # Генерація відповіді через AI
    return await _generate_ai_response(message, user_message)

# Допоміжні функції
def _is_greeting(text: str) -> bool:
    """Перевіряє, чи є повідомлення привітанням"""
    ...

async def _handle_greeting(message: Message):
    """Обробка привітань"""
    ...

# ... інші допоміжні функції
```

---

### **Етап 10: Оновлення main.py** ⏱️ 15 хвилин

#### 10.1. Оновлення імпорту
```python
# Старий імпорт
from handlers import router

# Новий імпорт (працює так само)
from handlers import router
# або
from handlers import main_router as router
```

---

### **Етап 11: Тестування** ⏱️ 2 години

#### 11.1. Чек-лист тестування:
- [ ] Всі команди працюють (`/start`, `/help`, `/stats`, `/history`)
- [ ] Всі кнопки меню працюють
- [ ] Чат з AI працює коректно
- [ ] Нагадування створюються та відображаються
- [ ] Налаштування зберігаються
- [ ] Callback queries працюють
- [ ] Немає помилок імпортів
- [ ] Логування працює

#### 11.2. Тестові сценарії:
1. Реєстрація нового користувача (`/start`)
2. Перегляд статистики (`/stats`)
3. Перегляд історії (`/history`)
4. Створення нагадування
5. Зміна спеціалізації
6. Задання різних типів питань (документи, вартість, факультети)
7. Використання callback queries

---

### **Етап 12: Очищення** ⏱️ 30 хвилин

#### 12.1. Видалення старого файлу
```bash
# Після успішного тестування
mv handlers.py handlers.py.backup
```

#### 12.2. Перевірка залежностей
- Перевірити, чи всі імпорти оновлені
- Перевірити, чи немає залишкових посилань на старий файл

---

## 📅 Графік виконання

### День 1 (4-5 годин):
- ✅ Етап 1: Підготовка (30 хв)
- ✅ Етап 2: Винесення утиліт (1 год)
- ✅ Етап 3: Винесення FSM станів (15 хв)
- ✅ Етап 4: Команди (1 год)
- ✅ Етап 5: Обробка меню (1.5 год)

### День 2 (4-5 годин):
- ✅ Етап 6: Налаштування (1 год)
- ✅ Етап 7: Нагадування (1.5 год)
- ✅ Етап 8: Callback queries (1 год)
- ✅ Етап 9: Чат з AI (початок, 1-2 год)

### День 3 (4-5 годин):
- ✅ Етап 9: Чат з AI (завершення, 2-3 год)
- ✅ Етап 10: Оновлення main.py (15 хв)
- ✅ Етап 11: Тестування (2 год)
- ✅ Етап 12: Очищення (30 хв)

**Загальний час:** 12-15 годин (3 робочі дні)

---

## ⚠️ Ризики та мітигація

### Ризик 1: Помилки імпортів
**Мітигація:**
- Використовувати абсолютні імпорти
- Перевіряти всі імпорти після кожного етапу
- Створити тести для перевірки імпортів

### Ризик 2: Втрата функціональності
**Мітигація:**
- Ретельне тестування після кожного етапу
- Збереження backup старого файлу
- Поступова міграція (не все одразу)

### Ризик 3: Циклічні залежності
**Мітигація:**
- Чітке визначення залежностей між модулями
- Винесення спільних функцій в `utils.py`
- Використання `__init__.py` для експорту

---

## ✅ Критерії успіху

1. ✅ Всі функції працюють як раніше
2. ✅ Код розбитий на логічні модулі
3. ✅ Кожен модуль < 500 рядків
4. ✅ Немає дублювання коду
5. ✅ Всі тести проходять
6. ✅ Немає помилок логування
7. ✅ Покращена читабельність коду

---

## 📝 Чек-лист виконання

### Підготовка:
- [ ] Створено структуру директорій
- [ ] Створено `__init__.py` з router
- [ ] Створено `utils.py` з допоміжними функціями
- [ ] Створено `states.py` з FSM станами

### Міграція модулів:
- [ ] Мігровано `commands.py`
- [ ] Мігровано `menu_handlers.py`
- [ ] Мігровано `settings.py`
- [ ] Мігровано `reminders.py`
- [ ] Мігровано `callbacks.py`
- [ ] Мігровано `chat_handler.py`

### Інтеграція:
- [ ] Оновлено `main.py`
- [ ] Перевірено всі імпорти
- [ ] Видалено застарілі імпорти

### Тестування:
- [ ] Протестовано всі команди
- [ ] Протестовано всі кнопки меню
- [ ] Протестовано чат з AI
- [ ] Протестовано нагадування
- [ ] Протестовано налаштування
- [ ] Протестовано callback queries

### Завершення:
- [ ] Створено backup старого файлу
- [ ] Видалено старий `handlers.py`
- [ ] Оновлено документацію
- [ ] Коміт змін в git

---

## 🎯 Наступні кроки після рефакторингу

1. **Додавання тестів** - створити unit-тести для кожного модуля
2. **Покращення логування** - додати структуроване логування
3. **Додавання type hints** - покращити типізацію
4. **Документація** - додати docstrings до всіх функцій

---

## 💡 Поради

1. **Робіть поступово** - не намагайтеся мігрувати все одразу
2. **Тестуйте після кожного етапу** - це допоможе виявити помилки раніше
3. **Зберігайте backup** - на випадок, якщо щось піде не так
4. **Використовуйте git** - комітьте після кожного успішного етапу
5. **Пишіть коментарі** - допоможе іншим розробникам зрозуміти структуру

---

## 📚 Додаткові ресурси

- [aiogram Router Documentation](https://docs.aiogram.dev/en/latest/dispatcher/router.html)
- [Python Package Structure](https://docs.python.org/3/tutorial/modules.html#packages)
- [Refactoring Best Practices](https://refactoring.guru/refactoring)

