"""
"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command, CommandStart
from database import db
from knowledge_base import get_knu_contacts
from keyboards import get_main_menu
from config import ADMIN_ID

router = Router(name="commands")


@router.message(Command("test"))
async def cmd_test(message: Message):
    """Тестова команда для перевірки роботи команд"""
    await message.answer("✅ Команди працюють! Це тестова команда /test")


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обробка команди /start"""
    user = message.from_user
    
    # Реєстрація користувача
    await db.register_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    welcome_text = (
        f"👋 <b>Вітаю, {user.first_name}!</b>\n\n"
        "Я - твій інтелектуальний помічник абітурієнта "
        "<b>Херсонського державного університету (ХДУ)</b>.\n\n"
        "<b>Що я можу:</b>\n"
        "💬 Відповісти на питання про вступ\n"
        "📚 Надати персональні поради\n"
        "📄 Розповісти про документи\n"
        "📞 Допомогти з контактами\n"
        "⏰ Нагадати про важливі дати\n\n"
        "Обери опцію з меню або просто напиши питання! 👇"
    )
    
    # Використовуємо явну перевірку для адміна
    menu = get_main_menu(user_id=user.id)
    await message.answer(welcome_text, reply_markup=menu, parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обробка команди /help"""
    help_text = (
        "📖 Довідка по боту ХДУ:\n\n"
        "/start - Почати роботу з ботом\n"
        "/help - Показати цю довідку\n"
        "/advice - Отримати поради щодо вступу до ХДУ\n"
        "/documents - Переглянути список документів для ХДУ\n"
        "/contacts - Контакти приймальної комісії ХДУ\n"
        "/reminders - Мої нагадування\n\n"
        "Або використовуй кнопки меню для навігації!\n\n"
        "💡 Цей бот допомагає з вступом до <b>Херсонського державного університету (ХДУ)</b>"
    )
    await message.answer(help_text, reply_markup=get_main_menu(user_id=message.from_user.id), parse_mode="HTML")


@router.message(Command("contacts"))
async def cmd_contacts(message: Message):
    """Обробка команди /contacts"""
    contacts = get_knu_contacts()
    await message.answer(contacts, reply_markup=get_main_menu(user_id=message.from_user.id), parse_mode="HTML")


@router.message(Command("check_admin"))
async def cmd_check_admin(message: Message):
    """Команда для перевірки налаштування адміна"""
    import os
    from dotenv import load_dotenv
    from config import ADMIN_ID
    from keyboards import get_main_menu
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Перезавантажуємо .env для перевірки
    load_dotenv()
    admin_id_from_env = os.getenv("ADMIN_ID", "0")
    
    user_id = message.from_user.id
    
    # Логування для debug
    logger.info(f"Check Admin - User ID: {user_id}, Type: {type(user_id)}")
    logger.info(f"Check Admin - ADMIN_ID from config: {ADMIN_ID}, Type: {type(ADMIN_ID)}")
    logger.info(f"Check Admin - ADMIN_ID from env: {admin_id_from_env}")
    
    # Перевірка через рядки та числа
    admin_match_str = str(ADMIN_ID).strip() == str(user_id).strip()
    admin_match_int = False
    try:
        admin_match_int = int(ADMIN_ID) == int(user_id)
    except (ValueError, TypeError):
        pass
    
    admin_match = admin_match_str or admin_match_int
    
    check_result = (
        f"🔍 <b>Детальна перевірка адміна:</b>\n\n"
        f"👤 Ваш Telegram ID: <code>{user_id}</code>\n"
        f"   Тип: <code>{type(user_id).__name__}</code>\n\n"
        f"⚙️ ADMIN_ID з config.py: <code>{ADMIN_ID}</code>\n"
        f"   Тип: <code>{type(ADMIN_ID).__name__}</code>\n\n"
        f"📄 ADMIN_ID з .env: <code>{admin_id_from_env}</code>\n\n"
        f"🔗 Порівняння через рядки: {'✅ СОВПАДАЄ' if admin_match_str else '❌ НЕ СОВПАДАЄ'}\n"
        f"🔗 Порівняння через числа: {'✅ СОВПАДАЄ' if admin_match_int else '❌ НЕ СОВПАДАЄ'}\n\n"
    )
    
    if ADMIN_ID and ADMIN_ID != 0 and admin_match:
        check_result += "✅ <b>ВИ АДМІНІСТРАТОР!</b>\n\n"
        check_result += "Натисніть /refresh_menu або /start щоб оновити меню."
    elif ADMIN_ID == 0 or not admin_id_from_env or admin_id_from_env == "0":
        check_result += "❌ <b>ADMIN_ID не встановлено</b>\n\n"
        check_result += "Встановіть в .env:\n<code>ADMIN_ID=ваш_telegram_id</code>\n\n"
        check_result += f"Ваш ID: <code>{user_id}</code>\n\n"
        check_result += "Після цього перезапустіть бота!"
    else:
        check_result += f"❌ <b>Ви НЕ адміністратор</b>\n\n"
        check_result += f"Ваш ID (<code>{user_id}</code>) ≠ ADMIN_ID (<code>{ADMIN_ID}</code>)\n\n"
        check_result += "Перевірте .env файл!"
    
    # Створюємо меню для перевірки
    test_menu = get_main_menu(user_id=user_id)
    
    await message.answer(check_result, reply_markup=test_menu, parse_mode="HTML")


@router.message(Command("refresh_menu"))
async def cmd_refresh_menu(message: Message):
    """Команда для оновлення меню (корисно для адмінів)"""
    from config import ADMIN_ID
    import os
    import logging
    
    logger = logging.getLogger(__name__)
    user_id = message.from_user.id
    
    # Діагностика
    admin_id_env = os.getenv("ADMIN_ID", "0")
    try:
        admin_id_env_int = int(admin_id_env.strip()) if admin_id_env.strip() else 0
    except:
        admin_id_env_int = 0
    
    logger.info(f"refresh_menu: user_id={user_id}, ADMIN_ID={ADMIN_ID}, env={admin_id_env_int}")
    
    menu = get_main_menu(user_id=user_id)
    await message.answer(
        f"🔄 <b>Меню оновлено!</b>\n\n"
        f"Ваш ID: <code>{user_id}</code>\n"
        f"ADMIN_ID: <code>{ADMIN_ID}</code>\n\n"
        "Якщо ви адміністратор, кнопка '🔐 Адмін панель' повинна з'явитися нижче.",
        reply_markup=menu,
        parse_mode="HTML"
    )


@router.message(Command("contacts_list"))
async def cmd_contacts_list(message: Message):
    """Команда для адміна - список поділених контактів"""
    if message.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await message.answer("❌ У вас немає доступу до цієї команди.")
        return
    
    contacts = await db.get_all_shared_contacts()
    
    if not contacts:
        await message.answer(
            "📋 <b>Список поділених контактів порожній</b>\n\n"
            "Поки що ніхто не поділився своїм контактом.",
            parse_mode="HTML"
        )
        return
    
    text = f"📋 <b>Список поділених контактів ({len(contacts)}):</b>\n\n"
    
    for i, contact in enumerate(contacts, 1):
        text += f"<b>{i}.</b> {contact['user_name']}\n"
        
        if contact['phone_number']:
            text += f"   📞 {contact['phone_number']}\n"
        
        if contact['telegram_first_name'] or contact['telegram_username']:
            text += "   👤 Telegram: "
            if contact['telegram_first_name']:
                text += contact['telegram_first_name']
            if contact['telegram_username']:
                text += f" (@{contact['telegram_username']})"
            text += "\n"
        
        text += f"   📅 {contact['created_at'].strftime('%d.%m.%Y %H:%M')}\n\n"
        
        if len(text) > 3500:  # Обмеження Telegram - розділяємо на частини
            await message.answer(text, parse_mode="HTML")
            text = ""
    
    if text:
        await message.answer(text, parse_mode="HTML")



