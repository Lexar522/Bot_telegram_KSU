"""
Обробники команд бота (/start, /help, /stats, /history, /contacts)
"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command, CommandStart
from database import db
from knowledge_base import get_knu_contacts
from keyboards import get_main_menu

router = Router()


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
        "⏰ Нагадати про важливі дати\n"
        "📊 Показати твою статистику\n\n"
        "Обери опцію з меню або просто напиши питання! 👇"
    )
    
    await message.answer(welcome_text, reply_markup=get_main_menu(), parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обробка команди /help"""
    help_text = (
        "📖 Довідка по боту ХДУ:\n\n"
        "/start - Почати роботу з ботом\n"
        "/help - Показати цю довідку\n"
        "/stats - Статистика користувача\n"
        "/history - Історія діалогів\n"
        "/advice - Отримати поради щодо вступу до ХДУ\n"
        "/documents - Переглянути список документів для ХДУ\n"
        "/contacts - Контакти приймальної комісії ХДУ\n"
        "/reminders - Мої нагадування\n\n"
        "Або використовуй кнопки меню для навігації!\n\n"
        "💡 Цей бот допомагає з вступом до <b>Херсонського державного університету (ХДУ)</b>"
    )
    await message.answer(help_text, reply_markup=get_main_menu(), parse_mode="HTML")


@router.message(Command("contacts"))
async def cmd_contacts(message: Message):
    """Обробка команди /contacts"""
    contacts = get_knu_contacts()
    await message.answer(contacts, reply_markup=get_main_menu())


@router.message(F.text.in_(["📊 Статистика", "/stats"]))
@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Статистика користувача"""
    stats = await db.get_user_stats(message.from_user.id)
    
    stats_text = (
        "📊 <b>Твоя статистика:</b>\n\n"
        f"💬 Задано питань: {stats['questions_count']}\n"
        f"⏰ Активних нагадувань: {stats['reminders_count']}\n"
    )
    
    if stats['registration_date']:
        stats_text += f"📅 Дата реєстрації: {stats['registration_date'].strftime('%d.%m.%Y')}\n"
    
    if stats['last_activity']:
        stats_text += f"🕐 Остання активність: {stats['last_activity'].strftime('%d.%m.%Y %H:%M')}\n"
    
    await message.answer(stats_text, reply_markup=get_main_menu(), parse_mode="HTML")


@router.message(F.text.in_(["📜 Історія", "/history"]))
@router.message(Command("history"))
async def cmd_history(message: Message):
    """Історія діалогів"""
    history = await db.get_message_history_with_ids(message.from_user.id, limit=10)
    
    if not history:
        await message.answer(
            "📜 Історія діалогів порожня.\n\n"
            "Почни діалог, задавши питання! 💬",
            reply_markup=get_main_menu()
        )
        return
    
    text = "📜 <b>Останні питання та відповіді:</b>\n\n"
    
    for i, msg in enumerate(reversed(history), 1):
        question = msg['user_message'][:60] + "..." if len(msg['user_message']) > 60 else msg['user_message']
        answer = msg['bot_response'][:60] + "..." if len(msg['bot_response']) > 60 else msg['bot_response']
        text += f"<b>{i}.</b> {question}\n   → {answer}\n\n"
        
        if len(text) > 3500:  # Обмеження Telegram
            text += "... (показано перші записи)"
            break
    
    await message.answer(text, reply_markup=get_main_menu(), parse_mode="HTML")



