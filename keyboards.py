"""
Клавіатури для Telegram-бота
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton




def get_specializations_keyboard():
    """Клавіатура вибору спеціалізації - покращена"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            # Перший рядок
            [
                KeyboardButton(text="💻 IT"),
                KeyboardButton(text="🏥 Медицина")
            ],
            # Другий рядок
            [
                KeyboardButton(text="⚖️ Право"),
                KeyboardButton(text="💰 Економіка")
            ],
            # Третій рядок
            [
                KeyboardButton(text="🎓 Педагогіка"),
                KeyboardButton(text="🔬 Природничі науки")
            ],
            # Четвертий рядок
            [
                KeyboardButton(text="📝 Інша"),
                KeyboardButton(text="⬅️ Назад")
            ]
        ],
        resize_keyboard=True
    )
    return keyboard


def get_back_keyboard():
    """Кнопка 'Назад' з головним меню"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⬅️ Назад")],
            [KeyboardButton(text="🏠 Головне меню")]
        ],
        resize_keyboard=True
    )
    return keyboard


def get_quick_actions_keyboard():
    """Швидкі дії для відповідей"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="💬 Інше питання"),
                KeyboardButton(text="📚 Поради")
            ],
            [
                KeyboardButton(text="🏠 Головне меню")
            ]
        ],
        resize_keyboard=True
    )
    return keyboard


def get_settings_keyboard():
    """Меню налаштувань - покращене"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🎯 Спеціалізація"),
                KeyboardButton(text="🔔 Нагадування")
            ],
            [
                KeyboardButton(text="🏠 Головне меню")
            ]
        ],
        resize_keyboard=True
    )
    return keyboard


def get_feedback_keyboard(message_history_id: int):
    """Inline клавіатура для повідомлення про помилку"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🚩 Повідомити про помилку",
                callback_data=f"report_{message_history_id}"
            )
        ]
    ])
    return keyboard


def get_reminders_management_keyboard():
    """Клавіатура для управління нагадуваннями - покращена"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="➕ Створити"),
                KeyboardButton(text="📋 Список")
            ],
            [
                KeyboardButton(text="🏠 Головне меню")
            ]
        ],
        resize_keyboard=True
    )
    return keyboard


def get_specialties_keyboard(faculty_id: str, report_id: int | None = None):
    """Inline клавіатура для вибору спеціальності факультету"""
    from knowledge_base import get_faculty_specialties_list
    
    specialties = get_faculty_specialties_list(faculty_id)
    buttons = []
    
    # Витягуємо номер факультету з faculty_id (наприклад, "1" з "faculty_1")
    faculty_num = faculty_id.replace("faculty_", "") if faculty_id.startswith("faculty_") else faculty_id
    
    # Створюємо кнопки для кожної спеціальності (по 1 в рядку через довгі назви)
    for idx, specialty in enumerate(specialties):
        # Обмежуємо довжину назви для кнопки (Telegram має ліміт на довжину тексту кнопки)
        button_text = specialty[:40] + "..." if len(specialty) > 40 else specialty
        buttons.append([
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"specialty_{faculty_num}_{idx}"
            )
        ])
    
    # Додаємо кнопку "Повернутись до факультетів"
    buttons.append([
        InlineKeyboardButton(
            text="⬅️ Повернутись до факультетів",
            callback_data="back_to_faculties"
        )
    ])
    
    # Якщо передано report_id, додаємо кнопку звіту
    if report_id is not None:
        buttons.append([
            InlineKeyboardButton(
                text="🚩 Повідомити про помилку",
                callback_data=f"report_{report_id}"
            )
        ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_faculties_keyboard(report_id: int | None = None):
    """Inline клавіатура для вибору факультету. Якщо передано report_id — додає кнопку 'Повідомити про помилку'."""
    from knowledge_base import get_faculties_list
    
    faculties = get_faculties_list()
    buttons = []
    
    # Створюємо кнопки по 2 в рядку
    for i in range(0, len(faculties), 2):
        row = []
        # Використовуємо id напряму (наприклад, "faculty_1")
        row.append(InlineKeyboardButton(
            text=faculties[i]["short"],
            callback_data=faculties[i]["id"]
        ))
        if i + 1 < len(faculties):
            row.append(InlineKeyboardButton(
                text=faculties[i + 1]["short"],
                callback_data=faculties[i + 1]["id"]
            ))
        buttons.append(row)
    
    # Додаємо кнопку "Повідомити про помилку", якщо потрібно
    if report_id is not None:
        buttons.append([
            InlineKeyboardButton(
                text="🚩 Повідомити про помилку",
                callback_data=f"report_{report_id}"
            )
        ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_contacts_keyboard():
    """Клавіатура для контактів з можливістю поділу свого контакту"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📤 Поділитися контактом")
            ],
            [
                KeyboardButton(text="🏠 Головне меню")
            ]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_share_contact_keyboard():
    """Клавіатура для поділу контакту (з request_contact=True)"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📤 Поділитися контактом", request_contact=True)
            ],
            [
                KeyboardButton(text="⬅️ Назад"),
                KeyboardButton(text="🏠 Головне меню")
            ]
        ],
        resize_keyboard=True
    )
    return keyboard


def get_main_menu(admin_id: int = None, user_id: int = None):
    """Головне меню бота - додає адмін-кнопку якщо користувач адмін"""
    from config import ADMIN_ID
    import logging
    import os
    
    logger = logging.getLogger(__name__)
    
    keyboard_buttons = [
        # Перший рядок - головна функція (найважливіша, на весь рядок для виділення)
        [
            KeyboardButton(text="💬 Задати питання")
        ],
        # Другий рядок - інформаційні розділи (3 кнопки)
        [
            KeyboardButton(text="📚 Поради"),
            KeyboardButton(text="📄 Документи"),
            KeyboardButton(text="📞 Контакти")
        ],
        # Третій рядок - нагадування, інфо та налаштування (3 кнопки)
        [
            KeyboardButton(text="⏰ Нагадування"),
            KeyboardButton(text="ℹ️ Інфо про бота"),
            KeyboardButton(text="⚙️ Налаштування")
        ]
    ]
    
    # Якщо користувач адмін - додаємо кнопку адмін-панелі
    check_user_id = user_id if user_id is not None else admin_id
    
    # Перевіряємо ADMIN_ID з os.getenv напряму для надійності
    admin_id_env = os.getenv("ADMIN_ID", "0")
    try:
        admin_id_env_int = int(admin_id_env.strip()) if admin_id_env.strip() else 0
    except (ValueError, TypeError):
        admin_id_env_int = 0
    
    # Розширена перевірка адміна
    is_admin = False
    if check_user_id:
        # Перевірка з config.ADMIN_ID
        if ADMIN_ID and ADMIN_ID != 0:
            try:
                if int(ADMIN_ID) == int(check_user_id):
                    is_admin = True
            except (ValueError, TypeError):
                pass
        
        # Перевірка з os.getenv (якщо перша не спрацювала)
        if not is_admin and admin_id_env_int and admin_id_env_int != 0:
            try:
                if int(admin_id_env_int) == int(check_user_id):
                    is_admin = True
            except (ValueError, TypeError):
                pass
        
        if is_admin:
            logger.info(f"✅ Admin menu added for user {check_user_id} (ADMIN_ID={ADMIN_ID}, env={admin_id_env_int})")
            # Додаємо адмін панель окремим рядком після всіх інших
            keyboard_buttons.append([
                KeyboardButton(text="🔐 Адмін панель")
            ])
        else:
            logger.debug(f"User {check_user_id} is not admin (ADMIN_ID={ADMIN_ID}, env={admin_id_env_int})")
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=keyboard_buttons,
        resize_keyboard=True,
        input_field_placeholder="Оберіть опцію або напиши питання"
    )
    return keyboard


def get_admin_menu():
    """Адмін-меню - доступне тільки для адміністратора"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="👥 Контакти абітурієнтів"),
                KeyboardButton(text="👤 Користувачі")
            ],
            [
                KeyboardButton(text="📢 Розсилка"),
                KeyboardButton(text="📊 Статистика бота")
            ],
            [
                KeyboardButton(text="💵 Управління вартістю")
            ],
            [
                KeyboardButton(text="⚙️ Налаштування сповіщень")
            ],
            [
                KeyboardButton(text="🏠 Головне меню")
            ]
        ],
        resize_keyboard=True
    )
    return keyboard

