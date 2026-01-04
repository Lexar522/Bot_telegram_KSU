"""
Обробники кнопок меню
"""
from aiogram import Router, F
from aiogram.types import Message, Contact, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import db
from knowledge_base import get_knu_contacts, get_admissions_committee_phones
from keyboards import (
    get_main_menu, get_back_keyboard, get_settings_keyboard,
    get_reminders_management_keyboard, get_admin_menu, get_contacts_keyboard,
    get_share_contact_keyboard
)

router = Router()


class ShareContactStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_contact = State()


class BroadcastStates(StatesGroup):
    waiting_for_content = State()  # Універсальний стан для будь-якого контенту
    confirming = State()


class UserSearchStates(StatesGroup):
    waiting_for_query = State()
    waiting_for_message_to_user = State()  # Для відправки повідомлень користувачу (текст, фото, відео)


class TuitionStates(StatesGroup):
    waiting_for_faculty = State()  # Вибір факультету
    waiting_for_specialty = State()  # Вибір спеціальності
    waiting_for_education_level = State()
    waiting_for_study_form = State()
    waiting_for_price_monthly = State()
    waiting_for_price_semester = State()
    waiting_for_price_year = State()
    waiting_for_price_total = State()
    waiting_for_specialty_code = State()
    confirming = State()


async def send_new_contact_notification_to_admin(
    contact_id: int,
    user_id: int,
    user_name: str,
    phone_number: str = None,
    first_name: str = None,
    last_name: str = None,
    username: str = None
):
    """Відправка повідомлення адміну про новий контакт"""
    from config import ADMIN_ID
    
    if not ADMIN_ID or ADMIN_ID == 0:
        return
    
    # Перевіряємо, чи сповіщення увімкнені
    notifications_enabled = await db.get_admin_notifications_setting(ADMIN_ID)
    if not notifications_enabled:
        return
    
    try:
        from aiogram import Bot
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        from config import BOT_TOKEN
        from datetime import datetime
        bot = Bot(token=BOT_TOKEN)
        
        # Отримуємо дату створення контакту
        contacts = await db.get_all_shared_contacts(only_unprocessed=True)
        contact_record = next((c for c in contacts if c.get('id') == contact_id), None)
        contact_date = contact_record['created_at'] if contact_record and contact_record.get('created_at') else datetime.now()
        
        text = (
            "🔔 <b>Новий контакт абітурієнта!</b>\n\n"
            f"👤 <b>Ім'я:</b> {user_name}\n"
        )
        
        if phone_number:
            # Форматуємо номер для клікабельності через HTML посилання
            phone_raw = str(phone_number).replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            # Додаємо + якщо його немає
            if not phone_raw.startswith('+'):
                phone_raw = '+' + phone_raw
            text += f"📞 <b>Телефон:</b> <a href=\"tel:{phone_raw}\">{phone_raw}</a>\n"
        
        if first_name or username:
            text += f"💬 <b>Telegram:</b> "
            if first_name:
                text += first_name
            if username:
                text += f" (@{username})"
            text += "\n"
        
        text += f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
        text += f"📅 <b>Дата:</b> {contact_date.strftime('%d.%m.%Y %H:%M') if isinstance(contact_date, datetime) else 'невідомо'}\n"
        
        # Створюємо inline кнопки для кожного окремого повідомлення
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Відмітити як опрацьований",
                    callback_data=f"mark_processed_{contact_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑️ Видалити контакт",
                    callback_data=f"confirm_delete_contact_{contact_id}"
                )
            ]
        ])
        
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
        await bot.session.close()
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Помилка відправки повідомлення адміну: {e}", exc_info=True)


@router.message(F.text.in_(["📚 Поради", "📚 Поради щодо вступу"]))
async def get_advice_handler(message: Message):
    """Обробка запиту на поради"""
    await message.answer("⏳ Формую персональні поради для тебе...")
    
    # Отримуємо спеціалізацію користувача
    user = await db.get_user(message.from_user.id)
    specialization = user.get("specialization") if user else None
    
    # Формуємо структуровану відповідь вручну
    response_text = "📚 <b>Поради щодо вступу до ХДУ</b>\n\n"
    
    # 1. Заява для вступу до ХДУ
    response_text += "📝 <b>Заява для вступу до ХДУ</b>\n\n"
    response_text += "Для подачі заяви потрібні такі документи:\n"
    response_text += "📄 • Заява (формується в електронному кабінеті вступника)\n"
    response_text += "🎓 • Документ про освіту (фотокопія, інформація міститься в ЄДЕБО. У разі відсутності, треба надати)\n"
    response_text += "📑 • Додаток до документа про освіту (об'єднати з самим документом – тобто документ про освіту та додаток до нього)\n"
    response_text += "🪪 • Фотокопія паспорта:\n"
    response_text += "   • Якщо це документ-книжечка: 1-2 сторінки та сторінка з місцем реєстрації\n"
    response_text += "   • Якщо це ID-картка: фото з 2-х сторін та витяг з реєстру територіальної громади з зазначенням місця реєстрації\n"
    response_text += "🔢 • Фотокопія ідентифікаційного коду\n"
    response_text += "⭐ • Документи про особливі права (пільговий вступ) (якщо є)\n\n"
    response_text += "⚠️ <i>Важливо:</i> Перевір актуальний список на офіційному сайті ХДУ або звернися до приймальної комісії.\n\n"
    
    # 2. Важливі дати для вступу
    response_text += "📅 <b>Важливі дати для вступу</b>\n\n"
    response_text += "📤 • Подача документів: згідно з графіком МОН України\n"
    response_text += "🏆 • Конкурсний відбір: після завершення подачі документів\n"
    response_text += "💰 • Вартість навчання 2025-2026 навчального року: уточнюй в приймальній комісії\n"
    response_text += "⏰ • Дедлайн: передбачається під час подачі заявки\n\n"
    
    # 3. Контакти приймальної комісії
    response_text += "📞 <b>Контакти приймальної комісії</b>\n\n"
    response_text += f"{get_admissions_committee_phones()}\n"
    response_text += "📍 Адреса: м. Херсон, вул. Університетська, 27\n\n"
    
    # Додаємо інформацію про рік навчання для вартості
    response_text += "<b>📅 Важливо:</b>\n"
    response_text += "• Вартість навчання вказана для <b>2025-2026 навчального року</b>\n"
    response_text += "• Для уточнення актуальної вартості звернися до приймальної комісії\n\n"
    
    # Якщо спеціалізація не встановлена, пропонуємо її встановити
    if not specialization:
        response_text += "💡 <i>Порада:</i> Встанови свою спеціалізацію в налаштуваннях для більш персоналізованих порад!"
    
    await message.answer(response_text, reply_markup=get_main_menu(user_id=message.from_user.id), parse_mode="HTML")


@router.message(F.text.in_(["📄 Документи", "📄 Список документів"]))
async def get_documents_handler(message: Message):
    """Обробка запиту на список документів"""
    documents_text = (
        "📄 <b>Список необхідних документів для вступу до ХДУ:</b>\n\n"
        "1. 📝 Заява (формується в електронному кабінеті вступника)\n"
        "2. 📜 Документ про освіту (фотокопія, інформація міститься в ЄДЕБО. У разі відсутності, треба надати)\n"
        "3. 📋 Додаток до документа про освіту (об'єднати з самим документом – тобто документ про освіту та додаток до нього)\n"
        "4. 🆔 Фотокопія паспорта:\n"
        "   • Якщо це документ-книжечка: 1-2 сторінки та сторінка з місцем реєстрації\n"
        "   • Якщо це ID-картка: фото з 2-х сторін та витяг з реєстру територіальної громади з зазначенням місця реєстрації\n"
        "5. 📄 Фотокопія ідентифікаційного коду\n"
        "6. ⭐ Документи про особливі права (пільговий вступ) (якщо є)\n\n"
        "💡 <i>Важливо:</i> Перевір актуальний список на офіційному сайті ХДУ або звернися до приймальної комісії!"
    )
    
    await message.answer(documents_text, reply_markup=get_main_menu(user_id=message.from_user.id), parse_mode="HTML")


@router.message(F.text.in_(["⏰ Нагадування", "⏰ Мої нагадування"]))
async def get_reminders_handler(message: Message):
    """Обробка запиту на нагадування"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Обробка запиту на нагадування для user_id={message.from_user.id}, текст: {message.text}")
    
    try:
        from datetime import datetime
        
        reminders = await db.get_user_reminders(message.from_user.id)
        logger.info(f"Знайдено нагадувань: {len(reminders) if reminders else 0}")
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        if not reminders:
            keyboard_buttons = [
                [
                    InlineKeyboardButton(
                        text="➕ Створити нагадування",
                        callback_data="reminder_create_new"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🏠 Головне меню",
                        callback_data="reminder_back_to_menu"
                    )
                ]
            ]
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            
            text = (
                "⏰ <b>Мої нагадування</b>\n\n"
                "📭 У тебе поки немає активних нагадувань.\n\n"
                "💡 <i>Порада:</i> Створи нагадування через кнопку нижче!"
            )
            
            await message.answer(
                text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            logger.info("Відправлено повідомлення про відсутність нагадувань")
        else:
            text = "⏰ <b>Мої нагадування:</b>\n\n"
            keyboard_buttons = []
            
            for reminder in reminders:
                reminder_id = reminder['id']
                deadline_date = reminder['deadline_date']
                deadline_name = reminder['deadline_name']
                is_sent = "✅" if reminder['is_sent'] else "⏳"
                days_left = (deadline_date - datetime.now().date()).days
                
                text += f"{is_sent} <b>{deadline_name}</b>\n"
                text += f"   📅 {deadline_date.strftime('%d.%m.%Y')} ({days_left} днів)\n\n"
                
                # Додаємо кнопку видалення для кожного нагадування
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text=f"🗑️ Видалити: {deadline_name[:30]}",
                        callback_data=f"reminder_delete_{reminder_id}"
                    )
                ])
            
            # Додаємо кнопку видалення всіх нагадувань
            if len(reminders) > 1:
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text="🗑️ Видалити всі нагадування",
                        callback_data="reminder_delete_all"
                    )
                ])
            
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text="⬅️ Назад до меню",
                    callback_data="reminder_back_to_menu"
                )
            ])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            
            await message.answer(
                text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            logger.info("Відправлено повідомлення зі списком нагадувань")
    except Exception as e:
        logger.error(f"Помилка обробки запиту на нагадування: {e}", exc_info=True)
        await message.answer(
            "❌ <b>Помилка</b>\n\n"
            "Не вдалося завантажити нагадування. Спробуй пізніше.",
            parse_mode="HTML"
        )


@router.message(F.text.in_(["📞 Контакти", "📞 Контакти ХДУ"]))
async def contacts_handler(message: Message):
    """Обробка запиту на контакти"""
    from keyboards import get_contacts_keyboard
    contacts = get_knu_contacts()
    await message.answer(contacts, reply_markup=get_contacts_keyboard(), parse_mode="HTML")


@router.message(F.text.in_(["📤 Поділитися контактом"]))
async def start_share_contact(message: Message, state: FSMContext):
    """Початок процесу поділу контакту - запитуємо ім'я"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        user_id = message.from_user.id
        logger.info(f"📤 Обробка поділу контакту для користувача {user_id}")
        
        # Перевіряємо, чи користувач вже поділився контактом
        has_contact = await db.has_shared_contact(user_id)
        logger.info(f"Перевірка контакту для {user_id}: {has_contact}")
        
        if has_contact:
            logger.info(f"Користувач {user_id} вже поділився контактом")
            # Отримуємо інформацію про збережений контакт
            contacts = await db.get_all_shared_contacts()
            user_contact = next((c for c in contacts if c.get('user_id') == user_id), None)
            
            if user_contact:
                contact_date = user_contact.get('created_at')
                contact_name = user_contact.get('user_name', 'Невідомо')
                contact_date_str = contact_date.strftime('%d.%m.%Y о %H:%M') if contact_date else 'невідомо'
                
                await message.answer(
                    "ℹ️ <b>Ви вже поділилися своїм контактом</b>\n\n"
                    f"📱 <b>Ваш контакт:</b>\n"
                    f"• Ім'я: {contact_name}\n"
                    f"• Дата поділу: {contact_date_str}\n\n"
                    "💡 <b>З вами зв'яжуться для надання повної інформації про вступ до ХДУ.</b>\n\n"
                    "🔄 Якщо вам потрібно оновити інформацію, зверніться до адміністратора.",
                    reply_markup=get_main_menu(user_id=user_id),
                    parse_mode="HTML"
                )
            else:
                await message.answer(
                    "ℹ️ <b>Ви вже поділилися своїм контактом</b>\n\n"
                    "💡 <b>З вами зв'яжуться для надання повної інформації про вступ до ХДУ.</b>\n\n"
                    "🔄 Якщо вам потрібно оновити інформацію, зверніться до адміністратора.",
                    reply_markup=get_main_menu(user_id=user_id),
                    parse_mode="HTML"
                )
            await state.clear()
            return
        
        current_state = await state.get_state()
        logger.info(f"Поточний стан для {user_id}: {current_state}")
        
        # Якщо вже в стані очікування контакту - просимо натиснути кнопку знову
        if current_state == ShareContactStates.waiting_for_contact:
            logger.info(f"Користувач {user_id} в стані waiting_for_contact")
            await message.answer(
                "ℹ️ Будь ласка, натисніть кнопку <b>\"📤 Поділитися контактом\"</b> нижче для поділу вашого контакту.",
                reply_markup=get_share_contact_keyboard(),
                parse_mode="HTML"
            )
            return
        
        # Якщо в стані очікування імені - не робимо нічого (чекаємо на текст)
        if current_state == ShareContactStates.waiting_for_name:
            logger.info(f"Користувач {user_id} в стані waiting_for_name")
            return
        
        # Початок процесу - запитуємо ім'я (не показуємо контакти ХДУ, одразу просимо ім'я)
        logger.info(f"Початок процесу поділу контакту для {user_id}")
        await message.answer(
            "📤 <b>Поділитись контактом</b>\n\n"
            "✏️ Будь ласка, введіть ваше ім'я для поділу контакту:\n\n"
            "<i>Наприклад: Іван, Марія, Олександр</i>",
            reply_markup=get_back_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(ShareContactStates.waiting_for_name)
        logger.info(f"Стан встановлено: waiting_for_name для {user_id}")
    except Exception as e:
        logger.error(f"Помилка в start_share_contact: {e}", exc_info=True)
        await message.answer(
            "❌ Сталася помилка. Спробуйте ще раз. 🔄",
            reply_markup=get_main_menu(user_id=message.from_user.id)
        )


@router.message(ShareContactStates.waiting_for_name)
async def process_contact_name(message: Message, state: FSMContext):
    """Обробка введеного імені"""
    if message.text == "⬅️ Назад" or message.text == "🏠 Головне меню":
        await state.clear()
        await message.answer("⬅️ Повертаємось до головного меню 👇", reply_markup=get_main_menu(user_id=message.from_user.id))
        return
    
    if not message.text or len(message.text.strip()) < 2:
        await message.answer(
            "❌ Будь ласка, введіть коректне ім'я (мінімум 2 символи) ✏️:",
            reply_markup=get_back_keyboard()
        )
        return
    
    user_name = message.text.strip()
    await state.update_data(user_name=user_name)
    
    await message.answer(
        f"✅ Ім'я збережено: <b>{user_name}</b>\n\n"
        "Тепер натисніть кнопку <b>\"📤 Поділитися контактом\"</b> нижче:",
        reply_markup=get_share_contact_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(ShareContactStates.waiting_for_contact)


@router.message(ShareContactStates.waiting_for_contact, F.contact)
async def share_contact_handler(message: Message, state: FSMContext):
    """Обробка поділу контакту після введення імені"""
    # Перевіряємо, чи користувач вже поділився контактом (на випадок, якщо щось пішло не так)
    has_contact = await db.has_shared_contact(message.from_user.id)
    if has_contact:
        # Отримуємо інформацію про збережений контакт
        contacts = await db.get_all_shared_contacts()
        user_contact = next((c for c in contacts if c.get('user_id') == message.from_user.id), None)
        
        if user_contact:
            contact_date = user_contact.get('created_at')
            contact_name = user_contact.get('user_name', 'Невідомо')
            contact_date_str = contact_date.strftime('%d.%m.%Y о %H:%M') if contact_date else 'невідомо'
            
            await message.answer(
                "ℹ️ <b>Ви вже поділилися своїм контактом</b>\n\n"
                f"📱 <b>Ваш контакт:</b>\n"
                f"• Ім'я: {contact_name}\n"
                f"• Дата поділу: {contact_date_str}\n\n"
                "💡 <b>З вами зв'яжуться для надання повної інформації про вступ до ХДУ.</b>\n\n"
                "Якщо вам потрібно оновити інформацію, зверніться до адміністратора.",
                reply_markup=get_main_menu(user_id=message.from_user.id),
                parse_mode="HTML"
            )
        else:
            await message.answer(
                "ℹ️ <b>Ви вже поділилися своїм контактом</b>\n\n"
                "💡 <b>З вами зв'яжуться для надання повної інформації про вступ до ХДУ.</b>\n\n"
                "Якщо вам потрібно оновити інформацію, зверніться до адміністратора.",
                reply_markup=get_main_menu(user_id=message.from_user.id),
                parse_mode="HTML"
            )
        await state.clear()
        return
    
    contact = message.contact
    
    if not contact:
        await message.answer("❌ Не вдалося отримати контакт. Спробуй ще раз. 🔄")
        return
    
    data = await state.get_data()
    user_name = data.get("user_name", "")
    
    # Зберігаємо контакт в БД (метод поверне contact_id або False, якщо контакт вже існує)
    contact_id = await db.save_shared_contact(
        user_id=message.from_user.id,
        user_name=user_name,
        phone_number=contact.phone_number,
        first_name=contact.first_name,
        last_name=contact.last_name,
        username=message.from_user.username
    )
    
    # Відправляємо повідомлення адміну про новий контакт
    if contact_id:
        await send_new_contact_notification_to_admin(
            contact_id=contact_id,
            user_id=message.from_user.id,
            user_name=user_name,
            phone_number=contact.phone_number,
            first_name=contact.first_name,
            last_name=contact.last_name,
            username=message.from_user.username
        )
    
    # Якщо контакт не був збережений (вже існує)
    if not contact_id:
        # Отримуємо інформацію про збережений контакт
        contacts = await db.get_all_shared_contacts()
        user_contact = next((c for c in contacts if c.get('user_id') == message.from_user.id), None)
        
        if user_contact:
            contact_date = user_contact.get('created_at')
            contact_name = user_contact.get('user_name', 'Невідомо')
            contact_date_str = contact_date.strftime('%d.%m.%Y о %H:%M') if contact_date else 'невідомо'
            
            await message.answer(
                "ℹ️ <b>Ви вже поділилися своїм контактом</b>\n\n"
                f"📱 <b>Ваш контакт:</b>\n"
                f"• Ім'я: {contact_name}\n"
                f"• Дата поділу: {contact_date_str}\n\n"
                "💡 <b>З вами зв'яжуться для надання повної інформації про вступ до ХДУ.</b>\n\n"
                "Якщо вам потрібно оновити інформацію, зверніться до адміністратора.",
                reply_markup=get_main_menu(user_id=message.from_user.id),
                parse_mode="HTML"
            )
        else:
            await message.answer(
                "ℹ️ <b>Ви вже поділилися своїм контактом</b>\n\n"
                "💡 <b>З вами зв'яжуться для надання повної інформації про вступ до ХДУ.</b>\n\n"
                "Якщо вам потрібно оновити інформацію, зверніться до адміністратора.",
                reply_markup=get_main_menu(user_id=message.from_user.id),
                parse_mode="HTML"
            )
        await state.clear()
        return
    
    contact_info = (
        "✅ <b>Дякуємо за поділ контакту!</b>\n\n"
        f"📱 <b>Ваш контакт збережено:</b>\n"
        f"• Ім'я: {user_name}\n"
    )
    
    if contact.phone_number:
        # Форматуємо номер для клікабельності через HTML посилання
        phone_raw = str(contact.phone_number).replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        # Додаємо + якщо його немає
        if not phone_raw.startswith('+'):
            phone_raw = '+' + phone_raw
        contact_info += f"• Телефон: <a href=\"tel:{phone_raw}\">{phone_raw}</a>"
    
    contact_info += (
        "\n\n"
        "💡 <b>З вами зв'яжуться для надання повної інформації про вступ до ХДУ.</b>\n\n"
        f"{get_admissions_committee_phones()}\n\n"
        "📍 м. Херсон, вул. Університетська, 27"
    )
    
    await message.answer(contact_info, reply_markup=get_main_menu(user_id=message.from_user.id), parse_mode="HTML")
    await state.clear()


@router.message(ShareContactStates.waiting_for_contact)
async def process_waiting_for_contact(message: Message, state: FSMContext):
    """Обробка інших повідомлень під час очікування контакту"""
    if message.text == "⬅️ Назад" or message.text == "🏠 Головне меню":
        await state.clear()
        await message.answer("⬅️ Повертаємось до головного меню 👇", reply_markup=get_main_menu(user_id=message.from_user.id))
        return
    
    # Якщо це не контакт і не навігація - просимо натиснути кнопку
    await message.answer(
        "ℹ️ Будь ласка, натисніть кнопку <b>\"📤 Поділитися контактом\"</b> нижче для поділу вашого контакту.",
        reply_markup=get_share_contact_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.contact)
async def handle_contact_without_state(message: Message, state: FSMContext):
    """Обробка контакту, якщо користувач поділився ним до введення імені"""
    current_state = await state.get_state()
    
    # Якщо вже в стані очікування контакту - передаємо в основний handler
    # Основний handler має вищий пріоритет через специфічний фільтр
    if current_state == ShareContactStates.waiting_for_contact:
        return  # Основний handler обробить
    
    # Якщо контакт прийшов без стану - просимо спочатку ввести ім'я
    # Перевіряємо, чи користувач вже поділився контактом
    has_contact = await db.has_shared_contact(message.from_user.id)
    if has_contact:
        # Отримуємо інформацію про збережений контакт
        contacts = await db.get_all_shared_contacts()
        user_contact = next((c for c in contacts if c.get('user_id') == message.from_user.id), None)
        
        if user_contact:
            contact_date = user_contact.get('created_at')
            contact_name = user_contact.get('user_name', 'Невідомо')
            contact_date_str = contact_date.strftime('%d.%m.%Y о %H:%M') if contact_date else 'невідомо'
            
            await message.answer(
                "ℹ️ <b>Ви вже поділилися своїм контактом</b>\n\n"
                f"📱 <b>Ваш контакт:</b>\n"
                f"• Ім'я: {contact_name}\n"
                f"• Дата поділу: {contact_date_str}\n\n"
                "💡 <b>З вами зв'яжуться для надання повної інформації про вступ до ХДУ.</b>\n\n"
                "Якщо вам потрібно оновити інформацію, зверніться до адміністратора.",
                reply_markup=get_main_menu(user_id=message.from_user.id),
                parse_mode="HTML"
            )
        else:
            await message.answer(
                "ℹ️ <b>Ви вже поділилися своїм контактом</b>\n\n"
                "💡 <b>З вами зв'яжуться для надання повної інформації про вступ до ХДУ.</b>\n\n"
                "Якщо вам потрібно оновити інформацію, зверніться до адміністратора.",
                reply_markup=get_main_menu(user_id=message.from_user.id),
                parse_mode="HTML"
            )
        await state.clear()
        return
    
    # Якщо контакт надійшов без попереднього введення імені - просимо спочатку ввести ім'я
    await message.answer(
        "📤 <b>Поділитись контактом</b>\n\n"
        "✏️ Спочатку будь ласка введіть ваше ім'я для поділу контакту:\n\n"
        "<i>Наприклад: Іван, Марія, Олександр</i>",
        reply_markup=get_back_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(ShareContactStates.waiting_for_name)


@router.message(F.text.in_(["💬 Задати питання", "💬 Інше питання"]))
async def ask_question_handler(message: Message):
    """Обробка запиту на питання"""
    await message.answer(
        "💬 <b>Задай своє питання про вступ до ХДУ</b>\n\n"
        "Я допоможу з:\n"
        "• Документами для вступу\n"
        "• Спеціальностями та вартістю навчання\n"
        "• Вступною кампанією\n"
        "• Підготовкою до вступу\n\n"
        "Просто напиши своє питання 👇",
        reply_markup=get_back_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "⬅️ Назад")
async def back_handler(message: Message):
    """Обробка кнопки 'Назад'"""
    await message.answer("⬅️ Повертаємось до головного меню 👇", reply_markup=get_main_menu(user_id=message.from_user.id))


@router.message(F.text == "🏠 Головне меню")
async def main_menu_handler(message: Message):
    """Повернення до головного меню"""
    await message.answer(
        "🏠 <b>Головне меню</b>\n\n"
        "Оберіть опцію:",
        reply_markup=get_main_menu(user_id=message.from_user.id),
        parse_mode="HTML"
    )


@router.message(F.text == "ℹ️ Інфо про бота")
async def bot_info_handler(message: Message):
    """Інформація про бота з профілем розробника"""
    from aiogram import Bot
    from config import BOT_TOKEN, ADMIN_ID
    
    try:
        bot = Bot(token=BOT_TOKEN)
        developer_username = "lexar_ko"
        developer_id = ADMIN_ID if ADMIN_ID and ADMIN_ID != 0 else None
        
        # Пробуємо отримати інформацію про розробника через ID (якщо він адмін)
        if developer_id:
            try:
                # Отримуємо інформацію про користувача через ID
                chat = await bot.get_chat(developer_id)
                
                first_name = chat.first_name or ""
                last_name = f" {chat.last_name}" if chat.last_name else ""
                full_name = (first_name + last_name).strip() or developer_username
                
                text = (
                    f"ℹ️ <b>Інформація про бота</b>\n\n"
                    f"⚠️ <b>Важливо:</b> Це <b>експериментальний проект</b>, який може працювати нестабільно та з помилками.\n\n"
                    f"📚 Цей проект був створений в рамках <b>навчального процесу</b> для університету.\n\n"
                    f"👨‍💻 <b>Розробник:</b> <a href=\"tg://user?id={developer_id}\">{full_name}</a>\n"
                    f"💬 <b>Username:</b> @{developer_username}\n\n"
                    f"🎓 <b>Призначення:</b>\n"
                    f"Бот призначений для допомоги абітурієнтам Херсонського державного університету (ХДУ) у процесі вступу.\n\n"
                    f"💡 <b>Функціонал:</b>\n"
                    f"• Консультації з питань вступу\n"
                    f"• Інформація про документи\n"
                    f"• Нагадування про важливі дати\n"
                    f"• Контакти приймальної комісії\n\n"
                    f"📧 <b>Для питань та пропозицій:</b> <a href=\"tg://user?id={developer_id}\">@{developer_username}</a>"
                )
                
                # Відправляємо лише текст без фото
                await message.answer(text, reply_markup=get_main_menu(user_id=message.from_user.id), parse_mode="HTML")
                
                await bot.session.close()
                return
                
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Не вдалося отримати профіль розробника через ID: {e}")
        
        # Fallback - використовуємо простий варіант з посиланням
        text = (
            "ℹ️ <b>Інформація про бота</b>\n\n"
            "⚠️ <b>Важливо:</b> Це <b>експериментальний проект</b>, який може працювати нестабільно та з помилками.\n\n"
            "📚 Цей проект був створений в рамках <b>навчального процесу</b> для університету.\n\n"
            f"👨‍💻 <b>Розробник:</b> <a href=\"tg://user?id={developer_id or ''}\">@{developer_username}</a>\n\n"
            "🎓 <b>Призначення:</b>\n"
            "Бот призначений для допомоги абітурієнтам Херсонського державного університету (ХДУ) у процесі вступу.\n\n"
            "💡 <b>Функціонал:</b>\n"
            "• Консультації з питань вступу\n"
            "• Інформація про документи\n"
            "• Нагадування про важливі дати\n"
            "• Контакти приймальної комісії\n\n"
            f"📧 <b>Для питань та пропозицій:</b> <a href=\"https://t.me/{developer_username}\">@{developer_username}</a>"
        )
        
        await message.answer(text, reply_markup=get_main_menu(user_id=message.from_user.id), parse_mode="HTML")
        await bot.session.close()
    
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Помилка в bot_info_handler: {e}", exc_info=True)
        
        # Fallback на простий варіант
        text = (
            "ℹ️ <b>Інформація про бота</b>\n\n"
            "⚠️ <b>Важливо:</b> Це <b>експериментальний проект</b>, який може працювати нестабільно та з помилками.\n\n"
            "📚 Цей проект був створений в рамках <b>навчального процесу</b> для університету.\n\n"
            "👨‍💻 <b>Розробник:</b> <a href=\"https://t.me/lexar_ko\">@lexar_ko</a>\n\n"
            "🎓 <b>Призначення:</b>\n"
            "Бот призначений для допомоги абітурієнтам Херсонського державного університету (ХДУ) у процесі вступу.\n\n"
            "💡 <b>Функціонал:</b>\n"
            "• Консультації з питань вступу\n"
            "• Інформація про документи\n"
            "• Нагадування про важливі дати\n"
            "• Контакти приймальної комісії\n\n"
            "📧 <b>Для питань та пропозицій:</b> <a href=\"https://t.me/lexar_ko\">@lexar_ko</a>"
        )
        await message.answer(text, reply_markup=get_main_menu(user_id=message.from_user.id), parse_mode="HTML")


@router.message(F.text == "🔐 Адмін панель")
async def admin_panel_handler(message: Message):
    """Обробка адмін-панелі - доступна тільки адміну"""
    from config import ADMIN_ID
    from keyboards import get_admin_menu
    
    if message.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await message.answer("❌ У вас немає доступу до цієї функції.", reply_markup=get_main_menu(user_id=message.from_user.id))
        return
    
    await message.answer(
        "🔐 <b>Адмін панель</b>\n\n"
        "Оберіть опцію:",
        reply_markup=get_admin_menu(),
        parse_mode="HTML"
    )


# ==================== УПРАВЛІННЯ КОРИСТУВАЧАМИ ====================

@router.message(F.text == "👤 Користувачі")
async def admin_users_handler(message: Message):
    """Меню управління користувачами"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"admin_users_handler викликано для користувача {message.from_user.id}")
    
    from config import ADMIN_ID
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    if message.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        logger.warning(f"Користувач {message.from_user.id} не має доступу (ADMIN_ID={ADMIN_ID})")
        await message.answer("❌ У вас немає доступу до цієї функції.", reply_markup=get_main_menu(user_id=message.from_user.id))
        return
    
    # Отримуємо загальну кількість користувачів
    total_count = 0
    try:
        if db.pool:
            async with db.pool.acquire() as conn:
                total_count = await conn.fetchval("SELECT COUNT(*) FROM users")
    except Exception as e:
        logger.error(f"Помилка отримання кількості користувачів: {e}")
    
    text = (
        f"👤 <b>Управління користувачами</b>\n\n"
        f"📊 <b>Всього користувачів:</b> {total_count}\n\n"
        f"Оберіть дію:"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Список користувачів", callback_data="users_list_0")
        ],
        [
            InlineKeyboardButton(text="🔍 Пошук користувача", callback_data="search_user")
        ]
    ])
    
    logger.info(f"Відправляємо меню управління користувачами")
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


# ==================== РОЗСИЛКА ====================

@router.message(F.text == "📢 Розсилка")
async def admin_broadcast_handler(message: Message):
    """Меню розсилок"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"admin_broadcast_handler викликано для користувача {message.from_user.id}")
    
    from config import ADMIN_ID
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    if message.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        logger.warning(f"Користувач {message.from_user.id} не має доступу до розсилки (ADMIN_ID={ADMIN_ID})")
        await message.answer("❌ У вас немає доступу до цієї функції.", reply_markup=get_main_menu(user_id=message.from_user.id))
        return
    
    text = (
        f"📢 <b>Розсилка повідомлень</b>\n\n"
        f"Оберіть аудиторію для розсилки:"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👥 Всі користувачі", callback_data="broadcast_all"),
            InlineKeyboardButton(text="✅ Тільки активні", callback_data="broadcast_active")
        ]
    ])
    
    logger.info(f"Відправляємо меню розсилок користувачу {message.from_user.id}")
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.message(F.text == "⚙️ Налаштування сповіщень")
async def admin_notifications_settings_handler(message: Message):
    """Налаштування сповіщень для адміна про нові контакти (запити на зателефонувати)"""
    from config import ADMIN_ID
    from keyboards import get_admin_menu
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    if message.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await message.answer("❌ У вас немає доступу до цієї функції.", reply_markup=get_main_menu(user_id=message.from_user.id))
        return
    
    notifications_enabled = await db.get_admin_notifications_setting(ADMIN_ID)
    unprocessed_count = await db.get_unprocessed_contacts_count()
    status_text = "увімкнені ✅" if notifications_enabled else "вимкнені ❌"
    
    text = (
        f"⚙️ <b>Налаштування сповіщень</b>\n\n"
        f"<b>Про що:</b> Сповіщення про нові запити абітурієнтів на зателефонувати\n\n"
        f"<b>Поточний стан:</b> сповіщення <b>{status_text}</b>\n\n"
        f"📊 <b>Неопрацьованих запитів:</b> {unprocessed_count}\n\n"
        f"Повідомлення приходять коли абітурієнт ділиться своїм контактом через бота.\n\n"
        f"Оберіть дію:"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Увімкнути сповіщення" if not notifications_enabled else "❌ Вимкнути сповіщення",
                callback_data="toggle_notifications"
            )
        ],
        [
            InlineKeyboardButton(
                text="📊 Статистика контактів",
                callback_data="contacts_stats"
            )
        ]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.message(F.text == "💵 Управління вартістю")
async def admin_tuition_handler(message: Message):
    """Меню управління вартістю навчання - вибір через факультет"""
    from config import ADMIN_ID
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from knowledge_base import get_faculties_list
    
    if message.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await message.answer("❌ У вас немає доступу до цієї функції.", reply_markup=get_main_menu(user_id=message.from_user.id))
        return
    
    # Отримуємо статистику вартостей
    all_prices = await db.get_all_tuition_prices()
    
    # Отримуємо список факультетів
    faculties = get_faculties_list()
    
    text = (
        f"💵 <b>Управління вартістю навчання</b>\n\n"
        f"📊 <b>Всього записів:</b> {len(all_prices)}\n\n"
        f"Оберіть факультет, щоб переглянути або додати вартість:"
    )
    
    # Створюємо кнопки з факультетами (по 2 в рядку)
    keyboard_buttons = []
    for i in range(0, len(faculties), 2):
        row = []
        for j in range(i, min(i + 2, len(faculties))):
            faculty = faculties[j]
            button_text = faculty.get('short', faculty.get('name', ''))[:30]
            # faculty['id'] вже має формат "faculty_1", тому просто додаємо префікс
            faculty_id_for_callback = faculty['id'].replace('faculty_', '') if faculty['id'].startswith('faculty_') else faculty['id']
            row.append(InlineKeyboardButton(
                text=button_text,
                callback_data=f"tuition_manage_faculty_{faculty_id_for_callback}"
            ))
        keyboard_buttons.append(row)
    
    keyboard_buttons.append([
        InlineKeyboardButton(text="🗑️ Очистити всі вартості", callback_data="tuition_confirm_delete_all")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.message(F.text == "👥 Контакти абітурієнтів")
async def admin_shared_contacts_handler(message: Message):
    """Обробка перегляду поділених контактів для адміна"""
    from config import ADMIN_ID
    from keyboards import get_admin_menu
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    if message.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await message.answer("❌ У вас немає доступу до цієї функції.", reply_markup=get_main_menu(user_id=message.from_user.id))
        return
    
    unprocessed_count = await db.get_unprocessed_contacts_count()
    all_contacts = await db.get_all_shared_contacts()
    
    text = (
        f"👥 <b>Управління контактами абітурієнтів</b>\n\n"
        f"📊 <b>Статистика:</b>\n"
        f"• Всього контактів: {len(all_contacts)}\n"
        f"• Неопрацьованих: {unprocessed_count}\n"
        f"• Опрацьованих: {len(all_contacts) - unprocessed_count}\n\n"
        f"Оберіть дію:"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"⏳ Неопрацьовані ({unprocessed_count})",
                callback_data="unprocessed_contacts"
            )
        ],
        [
            InlineKeyboardButton(
                text="👥 Всі контакти",
                callback_data="all_contacts"
            )
        ],
        [
            InlineKeyboardButton(
                text="🗑️ Очистити опрацьовані",
                callback_data="confirm_delete_processed"
            ),
            InlineKeyboardButton(
                text="🗑️ Очистити всі",
                callback_data="confirm_delete_all"
            )
        ]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.message(F.text == "📊 Статистика бота")
async def admin_bot_statistics_handler(message: Message):
    """Обробка перегляду статистики бота для адміна"""
    from config import ADMIN_ID
    from keyboards import get_admin_menu
    from datetime import datetime, timedelta
    
    if message.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await message.answer("❌ У вас немає доступу до цієї функції.", reply_markup=get_main_menu(user_id=message.from_user.id))
        return
    
    stats = await db.get_bot_statistics()
    
    text = "📊 <b>Статистика бота ХДУ</b>\n\n"
    
    # Загальна статистика
    text += "👥 <b>Користувачі:</b>\n"
    text += f"   • Всього користувачів: {stats['total_users']}\n"
    text += f"   • Активних: {stats['active_users']}\n"
    text += f"   • Активних сьогодні: {stats['users_today']}\n"
    text += f"   • Активних за тиждень: {stats['users_week']}\n"
    
    if stats['last_registration']:
        text += f"   • Остання реєстрація: {stats['last_registration'].strftime('%d.%m.%Y %H:%M')}\n"
    
    text += "\n💬 <b>Повідомлення:</b>\n"
    text += f"   • Всього повідомлень: {stats['total_messages']}\n"
    text += f"   • Сьогодні: {stats['messages_today']}\n"
    text += f"   • За тиждень: {stats['messages_week']}\n"
    
    if stats['total_messages'] > 0:
        avg_per_user = stats['total_messages'] / stats['total_users'] if stats['total_users'] > 0 else 0
        text += f"   • Середнє на користувача: {avg_per_user:.1f}\n"
    
    text += "\n⏰ <b>Нагадування:</b>\n"
    text += f"   • Всього нагадувань: {stats['total_reminders']}\n"
    text += f"   • Активних: {stats['active_reminders']}\n"
    text += f"   • Відправлено: {stats['sent_reminders']}\n"
    
    text += "\n👥 <b>Контакти абітурієнтів:</b>\n"
    text += f"   • Всього: {stats['total_shared_contacts']}\n"
    
    # Найактивніший користувач
    if stats['most_active_user']:
        user = stats['most_active_user']
        user_name = user.get('first_name', 'Невідомо')
        username = f"@{user.get('username')}" if user.get('username') else ""
        text += f"\n🏆 <b>Найактивніший користувач:</b>\n"
        text += f"   • {user_name} {username}\n"
        text += f"   • Повідомлень: {user.get('message_count', 0)}\n"
    
    # Статистика по спеціалізаціях
    if stats['specializations_stats']:
        text += "\n🎯 <b>Топ спеціалізацій:</b>\n"
        for i, spec in enumerate(stats['specializations_stats'][:5], 1):
            text += f"   {i}. {spec.get('specialization', 'Невідомо')}: {spec.get('count', 0)}\n"
    
    # Статистика по днях (останні 7 днів)
    if stats['daily_stats']:
        text += "\n📅 <b>Активність за останні 7 днів:</b>\n"
        for day_stat in stats['daily_stats'][:7]:
            date = day_stat.get('date')
            if date:
                if isinstance(date, str):
                    date_str = date
                else:
                    date_str = date.strftime('%d.%m')
                text += f"   • {date_str}: {day_stat.get('messages_count', 0)} повідомлень, {day_stat.get('users_count', 0)} користувачів\n"
    
    # Додаткова інформація
    text += "\n" + "=" * 40 + "\n"
    text += f"📊 Статистика зібрана: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
    
    # Розділяємо на частини якщо текст занадто довгий
    if len(text) > 4000:
        parts = text.split("\n\n")
        current_part = ""
        for part in parts:
            if len(current_part) + len(part) > 4000:
                await message.answer(current_part, reply_markup=get_admin_menu(), parse_mode="HTML")
                current_part = part + "\n\n"
            else:
                current_part += part + "\n\n"
        if current_part:
            await message.answer(current_part, reply_markup=get_admin_menu(), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=get_admin_menu(), parse_mode="HTML")


# ==================== ОБРОБКА FSM ДЛЯ РОЗСИЛОК ====================

@router.message(BroadcastStates.waiting_for_content)
async def process_broadcast_content(message: Message, state: FSMContext):
    """Автоматична обробка контенту для розсилки (визначає тип автоматично)"""
    from config import ADMIN_ID
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    if message.from_user.id != ADMIN_ID:
        await state.clear()
        return
    
    data = await state.get_data()
    send_to_active = data.get('send_to_active', False)
    
    # Визначаємо тип контенту автоматично
    broadcast_type = 'text'
    file_id = None
    caption = ""
    
    if message.photo:
        broadcast_type = 'photo'
        file_id = message.photo[-1].file_id
        caption = message.caption or ""
    elif message.video:
        broadcast_type = 'video'
        file_id = message.video.file_id
        caption = message.caption or ""
    elif message.document:
        broadcast_type = 'document'
        file_id = message.document.file_id
        caption = message.caption or ""
    elif message.text:
        broadcast_type = 'text'
        caption = message.text
    
    if not caption and broadcast_type == 'text':
        await message.answer("❌ Текст повідомлення не може бути порожнім 📝")
        return
    
    # Зберігаємо дані
    await state.update_data(
        broadcast_type=broadcast_type,
        broadcast_file_id=file_id,
        broadcast_text=caption
    )
    
    # Показуємо підтвердження
    confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Підтвердити розсилку", callback_data="broadcast_confirm_final")
        ],
        [
            InlineKeyboardButton(text="❌ Скасувати", callback_data="broadcast_cancel")
        ]
    ])
    
    type_names = {
        'text': '📝 Текст',
        'photo': '🖼️ Фото',
        'video': '📹 Відео',
        'document': '📎 Файл'
    }
    
    preview_text = (
        f"📢 <b>Попередній перегляд розсилки</b>\n\n"
        f"Тип: {type_names.get(broadcast_type, broadcast_type)}\n"
        f"Аудиторія: {'Активні користувачі' if send_to_active else 'Всі користувачі'}\n\n"
    )
    
    if broadcast_type == 'text':
        preview_text += f"{caption[:500]}{'...' if len(caption) > 500 else ''}\n\n"
    else:
        preview_text += f"Підпис: {caption if caption else '(без підпису)'}\n\n"
    
    preview_text += "Підтвердіть розсилку:"
    
    # Відправляємо прев'ю залежно від типу
    if broadcast_type == 'photo':
        await message.answer_photo(photo=file_id, caption=preview_text, reply_markup=confirm_keyboard, parse_mode="HTML")
    elif broadcast_type == 'video':
        await message.answer_video(video=file_id, caption=preview_text, reply_markup=confirm_keyboard, parse_mode="HTML")
    else:
        await message.answer(preview_text, reply_markup=confirm_keyboard, parse_mode="HTML")
    
    await state.set_state(BroadcastStates.confirming)


# ==================== ОБРОБКА FSM ДЛЯ ПОШУКУ КОРИСТУВАЧІВ ====================

@router.message(UserSearchStates.waiting_for_message_to_user)
async def process_message_to_user(message: Message, state: FSMContext):
    """Обробка відправки повідомлення користувачу (текст, фото, відео, файл)"""
    from config import ADMIN_ID
    
    if message.from_user.id != ADMIN_ID:
        await state.clear()
        return
    
    data = await state.get_data()
    target_user_id = data.get('target_user_id')
    
    if not target_user_id:
        await message.answer("❌ Помилка: не вказано користувача 👤")
        await state.clear()
        return
    
    # Обробляємо різні типи повідомлень
    try:
        if message.text:
            # Текстове повідомлення
            await send_message_to_user(message, target_user_id, message.text)
        elif message.photo:
            # Фото з підписом
            file_id = message.photo[-1].file_id
            caption = message.caption or ""
            await send_media_to_user(message, target_user_id, 'photo', file_id, caption)
        elif message.video:
            # Відео з підписом
            file_id = message.video.file_id
            caption = message.caption or ""
            await send_media_to_user(message, target_user_id, 'video', file_id, caption)
        elif message.document:
            # Файл з підписом
            file_id = message.document.file_id
            caption = message.caption or ""
            await send_media_to_user(message, target_user_id, 'document', file_id, caption)
        else:
            await message.answer("❌ Підтримуються тільки текст, фото, відео та файли")
        
        await state.clear()
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Помилка відправки повідомлення користувачу {target_user_id}: {e}", exc_info=True)
        await message.answer(f"❌ Помилка відправки: {e}")


@router.message(UserSearchStates.waiting_for_query)
async def process_user_search(message: Message, state: FSMContext):
    """Обробка пошуку користувача або відправки повідомлення"""
    from config import ADMIN_ID
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    if message.from_user.id != ADMIN_ID:
        await state.clear()
        return
    
    query = message.text.strip()
    data = await state.get_data()
    
    # Якщо це відправка повідомлення конкретному користувачу
    if 'target_user_id' in data:
        target_user_id = data['target_user_id']
        await send_message_to_user(message, target_user_id, query)
        await state.clear()
        return
    
    # Інакше це пошук користувача
    users = await db.search_users(query, limit=10)
    
    if not users:
        await message.answer(
            f"❌ Користувачів за запитом '<b>{query}</b>' не знайдено.",
            parse_mode="HTML"
        )
        await state.clear()
        return
    
    text = f"🔍 <b>Результати пошуку</b> (знайдено: {len(users)}):\n\n"
    
    for user in users:
        user_id = user['telegram_id']
        username = user.get('username', 'без username')
        first_name = user.get('first_name', '')
        last_name = user.get('last_name', '')
        is_blocked = user.get('is_blocked', False)
        status = "🚫" if is_blocked else "✅"
        
        user_info = (
            f"{status} <b>{first_name} {last_name}</b>\n"
            f"   💬 @{username}\n"
            f"   🆔 <code>{user_id}</code>\n\n"
        )
        
        user_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="👤 Профіль", callback_data=f"user_profile_{user_id}"),
                InlineKeyboardButton(text="💬 Написати", callback_data=f"send_to_user_{user_id}")
            ]
        ])
        
        await message.answer(user_info, reply_markup=user_keyboard, parse_mode="HTML")
    
    await state.clear()


async def send_message_to_user(message: Message, target_user_id: int, text: str):
    """Відправка текстового повідомлення користувачу"""
    from aiogram import Bot
    from config import BOT_TOKEN
    
    try:
        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(chat_id=target_user_id, text=text)
        await bot.session.close()
        await message.answer(f"✅ Повідомлення відправлено користувачу <code>{target_user_id}</code>", parse_mode="HTML")
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Помилка відправки повідомлення користувачу {target_user_id}: {e}")
        await message.answer(f"❌ Помилка відправки повідомлення: {e}")


async def send_media_to_user(message: Message, target_user_id: int, media_type: str, file_id: str, caption: str = ""):
    """Відправка медіа (фото, відео, файл) користувачу"""
    from aiogram import Bot
    from config import BOT_TOKEN
    
    try:
        bot = Bot(token=BOT_TOKEN)
        
        if media_type == 'photo':
            await bot.send_photo(chat_id=target_user_id, photo=file_id, caption=caption if caption else None)
        elif media_type == 'video':
            await bot.send_video(chat_id=target_user_id, video=file_id, caption=caption if caption else None)
        elif media_type == 'document':
            await bot.send_document(chat_id=target_user_id, document=file_id, caption=caption if caption else None)
        else:
            raise ValueError(f"Невідомий тип медіа: {media_type}")
        
        await bot.session.close()
        
        media_names = {'photo': 'Фото', 'video': 'Відео', 'document': 'Файл'}
        await message.answer(
            f"✅ {media_names.get(media_type, 'Медіа')} відправлено користувачу <code>{target_user_id}</code>",
            parse_mode="HTML"
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Помилка відправки {media_type} користувачу {target_user_id}: {e}", exc_info=True)
        await message.answer(f"❌ Помилка відправки {media_type}: {e}")


# ==================== FSM ДЛЯ УПРАВЛІННЯ ВАРТІСТЮ НАВЧАННЯ ====================



# ==================== FSM ДЛЯ УПРАВЛІННЯ ВАРТІСТЮ НАВЧАННЯ ====================
# Всі callback handlers для tuition знаходяться в handlers/admin_callbacks.py
# Тут тільки message handlers для введення цін


@router.message(TuitionStates.waiting_for_price_monthly)
async def process_price_monthly_for_tuition(message: Message, state: FSMContext):
    """Обробка вартості за місяць, автоматичний розрахунок семестру та року"""
    from config import ADMIN_ID
    
    if message.from_user.id != ADMIN_ID:
        await state.clear()
        return
    
    if message.text == "/skip":
        await message.answer("❌ Вартість за місяць обов'язкова. Спробуйте ще раз. 💰")
        return
    
    # Отримуємо число з повідомлення
    try:
        # Видаляємо всі символи крім цифр
        price_text = ''.join(filter(str.isdigit, message.text.strip()))
        if not price_text:
            await message.answer("❌ Будь ласка, введіть число (наприклад: 3683) 🔢")
            return
        
        price_monthly = int(price_text)
        if price_monthly <= 0:
            await message.answer("❌ Вартість повинна бути більше 0")
            return
        
        # Отримуємо дані зі стану
        data = await state.get_data()
        education_level = data.get('education_level', '').lower()
        
        # Розраховуємо вартість за семестр (5 місяців)
        price_semester = price_monthly * 5
        
        # Розраховуємо вартість за рік
        # Бакалавр: 10 місяців (2 семестри)
        # Магістр: також 10 місяців для стандартного розрахунку
        price_year = price_monthly * 10
        
        # Формуємо текст для збереження
        price_monthly_text = f"{price_monthly} грн/місяць"
        price_semester_text = f"{price_semester} грн/семестр"
        price_year_text = f"{price_year} грн/рік"
        
        # Отримуємо поточний навчальний рік для відображення
        current_academic_year = db.get_current_academic_year()
        
        # Зберігаємо вартість (academic_year автоматично встановиться)
        success = await db.set_tuition_price(
            specialty_name=data.get('specialty_name'),
            education_level=data.get('education_level'),
            study_form=data.get('study_form'),
            price_monthly=price_monthly_text,
            price_semester=price_semester_text,
            price_year=price_year_text,
            price_total=None,
            specialty_code=None,
            academic_year=None  # Автоматично встановиться поточний навчальний рік
        )
        
        if success:
            await message.answer(
                f"✅ <b>Вартість навчання збережено!</b>\n\n"
                f"📚 <b>Спеціальність:</b> {data.get('specialty_name')}\n"
                f"🎓 <b>Рівень:</b> {data.get('education_level').capitalize()}\n"
                f"📖 <b>Форма:</b> {data.get('study_form').capitalize()}\n"
                f"📅 <b>Навчальний рік:</b> {current_academic_year} (автоматично)\n\n"
                f"💰 <b>Розрахована вартість:</b>\n"
                f"• Місяць: {price_monthly_text}\n"
                f"• Семестр: {price_semester_text} (автоматично)\n"
                f"• Рік: {price_year_text} (автоматично)",
                parse_mode="HTML",
                reply_markup=get_admin_menu()
            )
        else:
            await message.answer(
                "❌ Помилка збереження вартості. Спробуйте ще раз. 💾",
                reply_markup=get_admin_menu()
            )
        
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Будь ласка, введіть коректне число (наприклад: 3683) 🔢")
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Помилка обробки вартості: {e}", exc_info=True)
        await message.answer(
            "❌ Помилка обробки вартості. Спробуйте ще раз. 🔄",
            reply_markup=get_admin_menu()
        )
        await state.clear()


# Callback handler для tuition_cancel знаходиться в handlers/admin_callbacks.py


