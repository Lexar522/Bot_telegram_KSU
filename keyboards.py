"""
Клавіатури для Telegram-бота
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu():
    """Головне меню бота - сучасне та зручне"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            # Перший рядок - основні функції
            [
                KeyboardButton(text="💬 Задати питання"),
                KeyboardButton(text="📚 Поради")
            ],
            # Другий рядок - інформація
            [
                KeyboardButton(text="📄 Документи"),
                KeyboardButton(text="📞 Контакти")
            ],
            # Третій рядок - особисті функції
            [
                KeyboardButton(text="⏰ Нагадування"),
                KeyboardButton(text="📊 Статистика")
            ],
            # Четвертий рядок - додаткові опції
            [
                KeyboardButton(text="⚙️ Налаштування")
            ]
        ],
        resize_keyboard=True,
        input_field_placeholder="Оберіть опцію або напиши питання"
    )
    return keyboard


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
                KeyboardButton(text="📜 Історія"),
                KeyboardButton(text="📊 Статистика")
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

