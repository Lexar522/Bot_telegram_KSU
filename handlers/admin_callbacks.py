"""
Callback handlers для адмін-панелі (користувачі, розсилки та вартість навчання)
"""
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.fsm.context import FSMContext
from database import db
from config import ADMIN_ID, BOT_TOKEN
from keyboards import get_admin_menu, get_main_menu
import logging

logger = logging.getLogger(__name__)

router = Router()


# ==================== УПРАВЛІННЯ КОРИСТУВАЧАМИ ====================

@router.callback_query(F.data.startswith("users_list_"))
async def users_list_handler(callback: CallbackQuery):
    """Список користувачів з пагінацією"""
    if callback.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await callback.answer("❌ У вас немає доступу", show_alert=True)
        return
    
    try:
        offset = int(callback.data.split("_")[-1])
        users = await db.get_all_users(limit=10, offset=offset)
        
        if not users and offset == 0:
            await callback.message.answer(
                "👤 <b>Користувачі не знайдені</b>",
                parse_mode="HTML"
            )
            await callback.answer()
            return
        
        text = f"👤 <b>Список користувачів</b>\n\n"
        
        for user in users:
            user_id = user['telegram_id']
            username = user.get('username', 'без username')
            first_name = user.get('first_name', '')
            last_name = user.get('last_name', '')
            messages_count = user.get('messages_count', 0)
            is_blocked = user.get('is_blocked', False)
            status = "🚫" if is_blocked else "✅"
            
            text += f"{status} <b>{first_name} {last_name}</b>\n"
            text += f"   💬 @{username}\n"
            text += f"   🆔 <code>{user_id}</code>\n"
            text += f"   📊 Повідомлень: {messages_count}\n"
            
            # Кнопки для кожного користувача
            user_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="👤 Профіль",
                        callback_data=f"user_profile_{user_id}"
                    ),
                    InlineKeyboardButton(
                        text="💬 Написати",
                        callback_data=f"send_to_user_{user_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🚫 Заблокувати" if not is_blocked else "✅ Розблокувати",
                        callback_data=f"toggle_block_{user_id}"
                    )
                ]
            ])
            
            await callback.message.answer(text, reply_markup=user_keyboard, parse_mode="HTML")
            text = ""
        
        # Кнопки навігації
        nav_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=f"users_list_{max(0, offset - 10)}"
                ) if offset > 0 else InlineKeyboardButton(text=" ", callback_data="none"),
                InlineKeyboardButton(
                    text="➡️ Далі",
                    callback_data=f"users_list_{offset + 10}"
                ) if len(users) == 10 else InlineKeyboardButton(text=" ", callback_data="none")
            ]
        ])
        
        if text or offset == 0:
            await callback.message.answer("Оберіть користувача:", reply_markup=nav_keyboard)
        
        await callback.answer()
    except Exception as e:
        logger.error(f"Помилка показу списку користувачів: {e}", exc_info=True)
        await callback.answer("❌ Помилка при завантаженні", show_alert=True)


@router.callback_query(F.data.startswith("user_profile_"))
async def user_profile_handler(callback: CallbackQuery):
    """Профіль користувача з детальною інформацією"""
    if callback.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await callback.answer("❌ У вас немає доступу", show_alert=True)
        return
    
    try:
        user_id = int(callback.data.split("_")[-1])
        # Отримуємо користувача з додатковою інформацією
        user_full = await db.get_user_by_id(user_id)
        
        if not user_full:
            await callback.answer("❌ Користувач не знайдено", show_alert=True)
            return
        
        is_blocked = user_full.get('is_blocked', False)
        messages_count = user_full.get('messages_count', 0)
        last_activity = user_full.get('last_activity')
        specialization = user_full.get('specialization', 'не встановлена')
        registration_date = user_full.get('registration_date')
        
        user = user_full  # Для сумісності з рештою коду
        
        text = (
            f"👤 <b>Профіль користувача</b>\n\n"
            f"<b>Ім'я:</b> {user.get('first_name', '')} {user.get('last_name', '')}\n"
            f"<b>Username:</b> @{user.get('username', 'без username')}\n"
            f"<b>ID:</b> <code>{user_id}</code>\n"
            f"<b>Статус:</b> {'🚫 Заблокований' if is_blocked else '✅ Активний'}\n"
            f"<b>Спеціалізація:</b> {specialization}\n"
            f"<b>Повідомлень:</b> {messages_count}\n"
        )
        
        if registration_date:
            text += f"<b>Реєстрація:</b> {registration_date.strftime('%d.%m.%Y %H:%M')}\n"
        if last_activity:
            text += f"<b>Остання активність:</b> {last_activity.strftime('%d.%m.%Y %H:%M')}\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💬 Написати користувачу",
                    callback_data=f"send_to_user_{user_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🚫 Заблокувати" if not is_blocked else "✅ Розблокувати",
                    callback_data=f"toggle_block_{user_id}"
                )
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="users_list_0")
            ]
        ])
        
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
    except Exception as e:
        logger.error(f"Помилка показу профілю користувача: {e}", exc_info=True)
        await callback.answer("❌ Помилка при завантаженні", show_alert=True)


@router.callback_query(F.data.startswith("toggle_block_"))
async def toggle_block_user_handler(callback: CallbackQuery):
    """Блокування/розблокування користувача"""
    if callback.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await callback.answer("❌ У вас немає доступу", show_alert=True)
        return
    
    try:
        user_id = int(callback.data.split("_")[-1])
        is_blocked = await db.is_user_blocked(user_id)
        
        if is_blocked:
            await db.unblock_user(user_id)
            await callback.answer("✅ Користувача розблоковано")
        else:
            await db.block_user(user_id, ADMIN_ID, "Заблоковано адміністратором")
            await callback.answer("🚫 Користувача заблоковано")
        
        # Оновлюємо повідомлення
        await callback.answer("✅ Статус оновлено")
    except Exception as e:
        logger.error(f"Помилка блокування користувача: {e}", exc_info=True)
        await callback.answer("❌ Помилка при обробці", show_alert=True)


@router.callback_query(F.data.startswith("send_to_user_"))
async def send_to_user_handler(callback: CallbackQuery, state: FSMContext):
    """Початок відправки повідомлення користувачу"""
    if callback.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await callback.answer("❌ У вас немає доступу", show_alert=True)
        return
    
    try:
        user_id = int(callback.data.split("_")[-1])
        await state.update_data(target_user_id=user_id)
        
        await callback.message.answer(
            f"💬 <b>Відправка повідомлення користувачу</b>\n\n"
            f"🆔 ID: <code>{user_id}</code>\n\n"
            f"Надішліть:\n"
            f"• Текст повідомлення\n"
            f"• Фото з підписом\n"
            f"• Відео з підписом\n"
            f"• Файл з підписом",
            parse_mode="HTML"
        )
        await callback.answer()
        
        # Встановлюємо стан для відправки повідомлень
        from handlers.menu_handlers import UserSearchStates
        await state.set_state(UserSearchStates.waiting_for_message_to_user)
    except Exception as e:
        logger.error(f"Помилка відправки користувачу: {e}", exc_info=True)
        await callback.answer("❌ Помилка", show_alert=True)


@router.callback_query(F.data == "search_user")
async def search_user_handler(callback: CallbackQuery, state: FSMContext):
    """Пошук користувача"""
    if callback.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await callback.answer("❌ У вас немає доступу", show_alert=True)
        return
    
    await callback.message.answer(
        "🔍 <b>Пошук користувача</b>\n\n"
        "🔍 Введіть ID, username або ім'я користувача:",
        parse_mode="HTML"
    )
    await callback.answer()
    
    from handlers.menu_handlers import UserSearchStates
    await state.set_state(UserSearchStates.waiting_for_query)


# ==================== РОЗСИЛКИ ====================

@router.callback_query(F.data.in_(["broadcast_all", "broadcast_active"]))
async def broadcast_start_handler(callback: CallbackQuery, state: FSMContext):
    """Початок створення розсилки - зберігаємо тип аудиторії"""
    if callback.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await callback.answer("❌ У вас немає доступу", show_alert=True)
        return
    
    send_to_active = "active" in callback.data
    await state.update_data(send_to_active=send_to_active)
    
    await callback.message.answer(
        f"📢 <b>Розсилка {'активним користувачам' if send_to_active else 'всім користувачам'}</b>\n\n"
        f"Надішліть повідомлення для розсилки:\n"
        f"• Текст\n"
        f"• Фото з підписом\n"
        f"• Відео з підписом\n"
        f"• Файл з підписом\n\n"
        f"Тип визначиться автоматично.",
        parse_mode="HTML"
    )
    await callback.answer()
    
    from handlers.menu_handlers import BroadcastStates
    await state.set_state(BroadcastStates.waiting_for_content)


# ==================== ПІДТВЕРДЖЕННЯ ТА ВИКОНАННЯ РОЗСИЛОК ====================

@router.callback_query(F.data == "broadcast_confirm_final")
async def broadcast_confirm_handler(callback: CallbackQuery, state: FSMContext):
    """Підтвердження та виконання розсилки"""
    if callback.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await callback.answer("❌ У вас немає доступу", show_alert=True)
        return
    
    try:
        data = await state.get_data()
        send_to_active = data.get('send_to_active', False)
        
        broadcast_type = data.get('broadcast_type', 'text')
        broadcast_text = data.get('broadcast_text', '')
        broadcast_file_id = data.get('broadcast_file_id')
        
        # Створюємо запис розсилки
        broadcast_id = await db.create_broadcast(
            admin_id=ADMIN_ID,
            message_text=broadcast_text,
            message_type=broadcast_type,
            file_id=broadcast_file_id,
            send_to_active_only=send_to_active
        )
        
        # Отримуємо список користувачів для розсилки
        if send_to_active:
            user_ids = await db.get_active_users(days=30)
        else:
            # Отримуємо всіх користувачів
            user_ids = await db.get_all_user_ids()
        
        # Виключаємо заблокованих користувачів
        filtered_user_ids = []
        for user_id in user_ids:
            if not await db.is_user_blocked(user_id):
                filtered_user_ids.append(user_id)
        
        total_users = len(filtered_user_ids)
        success_count = 0
        failed_count = 0
        
        # Відправляємо нове повідомлення про запуск розсилки (бо callback.message може бути з фото/відео)
        status_msg = await callback.message.answer(
            f"📢 <b>Розсилка запущена</b>\n\n"
            f"Тип: {broadcast_type}\n"
            f"Аудиторія: {'Активні користувачі' if send_to_active else 'Всі користувачі'}\n"
            f"Кількість: {total_users}\n\n"
            f"⏳ Відправка...",
            parse_mode="HTML"
        )
        
        # Відправляємо повідомлення
        bot = Bot(token=BOT_TOKEN)
        
        for user_id in filtered_user_ids:
            try:
                if broadcast_type == 'text':
                    if broadcast_text:  # Перевіряємо що текст не порожній
                        await bot.send_message(chat_id=user_id, text=broadcast_text)
                    else:
                        continue  # Пропускаємо якщо текст порожній
                elif broadcast_type == 'photo':
                    await bot.send_photo(
                        chat_id=user_id, 
                        photo=broadcast_file_id, 
                        caption=broadcast_text if broadcast_text else None
                    )
                elif broadcast_type == 'video':
                    await bot.send_video(
                        chat_id=user_id, 
                        video=broadcast_file_id, 
                        caption=broadcast_text if broadcast_text else None
                    )
                elif broadcast_type == 'document':
                    await bot.send_document(
                        chat_id=user_id, 
                        document=broadcast_file_id, 
                        caption=broadcast_text if broadcast_text else None
                    )
                
                success_count += 1
            except Exception as e:
                failed_count += 1
                logger.warning(f"Помилка відправки користувачу {user_id}: {e}")
        
        await bot.session.close()
        
        # Оновлюємо статус розсилки
        await db.update_broadcast_status(broadcast_id, 'sent', success_count, failed_count)
        
        # Редагуємо повідомлення про статус (воно завжди текстове)
        await status_msg.edit_text(
            f"✅ <b>Розсилка завершена</b>\n\n"
            f"Успішно: {success_count}\n"
            f"Помилок: {failed_count}\n"
            f"Всього: {total_users}",
            parse_mode="HTML"
        )
        
        await callback.answer("✅ Розсилка завершена")
        await state.clear()
        
    except Exception as e:
        logger.error(f"Помилка виконання розсилки: {e}", exc_info=True)
        await callback.answer("❌ Помилка при розсилці", show_alert=True)
        await state.clear()


@router.callback_query(F.data == "broadcast_cancel")
async def broadcast_cancel_handler(callback: CallbackQuery, state: FSMContext):
    """Скасування розсилки"""
    if callback.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await callback.answer("❌ У вас немає доступу", show_alert=True)
        return
    
    # Відправляємо нове повідомлення про скасування (бо callback.message може бути з фото/відео)
    await callback.message.answer("❌ Розсилку скасовано", parse_mode="HTML")
    await callback.answer("❌ Скасовано")
    await state.clear()


@router.callback_query(F.data == "none")
async def none_handler(callback: CallbackQuery):
    """Обробка пустих callback (заглушка)"""
    await callback.answer()


# ==================== УПРАВЛІННЯ ВАРТІСТЮ НАВЧАННЯ ====================

@router.callback_query(F.data.startswith("tuition_list_"))
async def tuition_list_handler(callback: CallbackQuery):
    """Список вартостей навчання з пагінацією"""
    if callback.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await callback.answer("❌ У вас немає доступу", show_alert=True)
        return
    
    try:
        offset = int(callback.data.split("_")[-1])
        all_prices = await db.get_all_tuition_prices()
        
        if not all_prices and offset == 0:
            await callback.message.answer(
                "💵 <b>Вартості не знайдені</b>\n\nСпочатку додайте вартість навчання.",
                reply_markup=get_admin_menu(),
                parse_mode="HTML"
            )
            await callback.answer()
            return
        
        # Пагінація
        page_size = 5
        total = len(all_prices)
        pages = (total + page_size - 1) // page_size
        current_page = offset // page_size
        
        prices_page = all_prices[offset:offset + page_size]
        
        text = f"💵 <b>Список вартостей навчання</b>\n\n"
        text += f"Сторінка {current_page + 1} з {pages}\n\n"
        
        for price in prices_page:
            specialty = price.get('specialty_name', 'Невідомо')
            code = price.get('specialty_code', '')
            level = price.get('education_level', '').capitalize()
            form = price.get('study_form', '').capitalize()
            monthly = price.get('price_monthly', 'не вказано')
            price_id = price['id']
            
            text += f"📚 <b>{specialty}</b>\n"
            if code:
                text += f"   Код: {code}\n"
            text += f"   {level} ({form}): {monthly}\n"
            text += f"   ID: {price_id}\n\n"
        
        keyboard_buttons = []
        
        # Кнопки навігації
        nav_buttons = []
        if offset > 0:
            nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"tuition_list_{offset - page_size}"))
        if offset + page_size < total:
            nav_buttons.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"tuition_list_{offset + page_size}"))
        
        if nav_buttons:
            keyboard_buttons.append(nav_buttons)
        
        # Додаємо кнопки видалення для кожної вартості на поточній сторінці (по 2 в рядку)
        delete_buttons_row = []
        for idx, price in enumerate(prices_page):
            price_id = price['id']
            specialty = price.get('specialty_name', 'Невідомо')
            level = price.get('education_level', '').capitalize()
            form = price.get('study_form', '').capitalize()
            # Створюємо короткий текст для кнопки
            button_text = f"🗑️ {specialty[:15]}... ({level[:1]}.{form[:1]})" if len(specialty) > 15 else f"🗑️ {specialty} ({level[:1]}.{form[:1]})"
            
            delete_buttons_row.append(
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"tuition_confirm_delete_{price_id}"
                )
            )
            
            # Додаємо по 2 кнопки в рядок
            if len(delete_buttons_row) == 2 or idx == len(prices_page) - 1:
                keyboard_buttons.append(delete_buttons_row)
                delete_buttons_row = []
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="➕ Додати вартість", callback_data="tuition_add")
        ])
        keyboard_buttons.append([
            InlineKeyboardButton(text="⬅️ Назад", callback_data="tuition_back_to_faculties")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        if callback.message.text:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        
        await callback.answer()
    except Exception as e:
        logger.error(f"Помилка отримання списку вартостей: {e}", exc_info=True)
        await callback.answer("❌ Помилка при отриманні списку", show_alert=True)


@router.callback_query(F.data.startswith("tuition_faculty_"))
async def tuition_faculty_selected_handler(callback: CallbackQuery, state: FSMContext):
    """Обробка вибору факультету для вартості"""
    if callback.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await callback.answer("❌ У вас немає доступу", show_alert=True)
        return
    
    from handlers.menu_handlers import TuitionStates
    from knowledge_base import get_faculty_specialties_list, get_faculties_list
    
    faculty_id = callback.data.replace("tuition_faculty_", "")
    
    # Зберігаємо факультет в стані
    await state.update_data(faculty_id=faculty_id)
    
    # Отримуємо назву факультету
    faculties = get_faculties_list()
    faculty_info = next((f for f in faculties if f['id'] == faculty_id), None)
    faculty_name = faculty_info.get('name', faculty_id) if faculty_info else faculty_id
    
    # Отримуємо список спеціальностей
    specialties = get_faculty_specialties_list(faculty_id)
    
    if not specialties:
        await callback.answer("❌ Спеціальності не знайдено", show_alert=True)
        return
    
    # Зберігаємо список спеціальностей в стані для подальшого використання
    await state.update_data(specialties_list=specialties, faculty_id=faculty_id)
    
    # Створюємо кнопки зі спеціальностями (по 1 в рядку через довгі назви)
    # Використовуємо індекс замість повної назви для callback_data
    keyboard_buttons = []
    for idx, specialty in enumerate(specialties):
        # Обмежуємо довжину назви для кнопки
        button_text = specialty[:40] + "..." if len(specialty) > 40 else specialty
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"tuition_spec_{idx}"
            )
        ])
    
    keyboard_buttons.append([
        InlineKeyboardButton(text="⬅️ Назад до факультетів", callback_data="tuition_add"),
        InlineKeyboardButton(text="❌ Скасувати", callback_data="tuition_cancel")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await callback.message.edit_text(
        f"💵 <b>Додавання вартості навчання</b>\n\n"
        f"📚 Факультет: <b>{faculty_name}</b>\n\n"
        f"Оберіть спеціальність:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(TuitionStates.waiting_for_specialty)
    await callback.answer()


@router.callback_query(F.data.startswith("tuition_spec_"))
async def tuition_specialty_selected_handler(callback: CallbackQuery, state: FSMContext):
    """Обробка вибору спеціальності для вартості"""
    if callback.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await callback.answer("❌ У вас немає доступу", show_alert=True)
        return
    
    # Отримуємо індекс спеціальності з callback_data
    try:
        specialty_idx = int(callback.data.replace("tuition_spec_", ""))
    except (ValueError, TypeError):
        await callback.answer("❌ Помилка вибору спеціальності", show_alert=True)
        return
    
    # Отримуємо список спеціальностей зі стану
    data = await state.get_data()
    specialties_list = data.get('specialties_list', [])
    
    if specialty_idx < 0 or specialty_idx >= len(specialties_list):
        await callback.answer("❌ Спеціальність не знайдена", show_alert=True)
        return
    
    # Отримуємо назву спеціальності за індексом
    specialty_name = specialties_list[specialty_idx]
    
    # Зберігаємо спеціальність в стані
    await state.update_data(specialty_name=specialty_name)
    
    # Отримуємо faculty_id для кнопки "Назад"
    faculty_id = data.get('faculty_id', '')
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Бакалавр", callback_data="tuition_level_бакалавр"),
            InlineKeyboardButton(text="Магістр", callback_data="tuition_level_магістр")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад до спеціальностей", callback_data=f"tuition_faculty_{faculty_id}"),
            InlineKeyboardButton(text="❌ Скасувати", callback_data="tuition_cancel")
        ]
    ])
    
    await callback.message.edit_text(
        f"💵 <b>Додавання вартості навчання</b>\n\n"
        f"📚 Спеціальність: <b>{specialty_name}</b>\n\n"
        f"Оберіть рівень освіти:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tuition_level_"))
async def tuition_level_selected_handler(callback: CallbackQuery, state: FSMContext):
    """Обробка вибору рівня освіти для вартості"""
    if callback.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await callback.answer("❌ У вас немає доступу", show_alert=True)
        return
    
    from handlers.menu_handlers import TuitionStates
    
    education_level = callback.data.replace("tuition_level_", "")
    await state.update_data(education_level=education_level)
    
    # Отримуємо дані зі стану для відображення
    data = await state.get_data()
    specialty_name = data.get('specialty_name', '')
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Денна", callback_data="tuition_form_денна"),
            InlineKeyboardButton(text="Заочна", callback_data="tuition_form_заочна")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад до спеціальностей", callback_data="tuition_add"),
            InlineKeyboardButton(text="❌ Скасувати", callback_data="tuition_cancel")
        ]
    ])
    
    await callback.message.edit_text(
        f"💵 <b>Додавання вартості навчання</b>\n\n"
        f"📚 Спеціальність: <b>{specialty_name}</b>\n"
        f"🎓 Рівень освіти: <b>{education_level.capitalize()}</b>\n\n"
        f"Оберіть форму навчання:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tuition_form_"))
async def tuition_form_selected_handler(callback: CallbackQuery, state: FSMContext):
    """Обробка вибору форми навчання для вартості"""
    if callback.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await callback.answer("❌ У вас немає доступу", show_alert=True)
        return
    
    from handlers.menu_handlers import TuitionStates
    
    study_form = callback.data.replace("tuition_form_", "")
    await state.update_data(study_form=study_form)
    
    # Отримуємо дані зі стану для відображення
    data = await state.get_data()
    specialty_name = data.get('specialty_name', '')
    education_level = data.get('education_level', '').capitalize()
    
    await callback.message.edit_text(
        f"💵 <b>Додавання вартості навчання</b>\n\n"
        f"📚 Спеціальність: <b>{specialty_name}</b>\n"
        f"🎓 Рівень освіти: <b>{education_level}</b>\n"
        f"📖 Форма навчання: <b>{study_form.capitalize()}</b>\n\n"
        f"💰 Введіть вартість за місяць (тільки число, наприклад: <b>3683</b>):\n"
        f"<i>Система автоматично розрахує вартість за семестр та рік</i>",
        parse_mode="HTML"
    )
    await state.set_state(TuitionStates.waiting_for_price_monthly)
    await callback.answer()


@router.callback_query(F.data == "tuition_cancel")
async def tuition_cancel_handler(callback: CallbackQuery, state: FSMContext):
    """Скасування додавання вартості"""
    if callback.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await callback.answer("❌ У вас немає доступу", show_alert=True)
        return
    
    await state.clear()
    
    # Повертаємо до меню управління вартістю
    from knowledge_base import get_faculties_list
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
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
    
    # Редагуємо повідомлення замість створення нового
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except:
        # Якщо не вдалося відредагувати (наприклад, повідомлення вже змінено), створюємо нове
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    
    await callback.answer("✅ Операцію скасовано")


@router.callback_query(F.data == "tuition_back_to_admin")
async def tuition_back_to_admin_handler(callback: CallbackQuery):
    """Повернення до адмін меню"""
    if callback.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await callback.answer("❌ У вас немає доступу", show_alert=True)
        return
    
    await callback.message.answer(
        "🏠 <b>Адмін панель</b>\n\nОберіть опцію:",
        reply_markup=get_admin_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "tuition_back_to_faculties")
async def tuition_back_to_faculties_handler(callback: CallbackQuery):
    """Повернення до списку факультетів в управлінні вартістю"""
    if callback.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await callback.answer("❌ У вас немає доступу", show_alert=True)
        return
    
    from knowledge_base import get_faculties_list
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
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
    
    if callback.message.text:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    
    await callback.answer()


@router.callback_query(F.data.startswith("tuition_manage_faculty_"))
async def tuition_manage_faculty_handler(callback: CallbackQuery, state: FSMContext):
    """Управління вартістю - вибір факультету"""
    if callback.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await callback.answer("❌ У вас немає доступу", show_alert=True)
        return
    
    from knowledge_base import get_faculty_specialties_list, get_faculties_list
    
    faculty_id = callback.data.replace("tuition_manage_faculty_", "")
    
    # Перевіряємо, чи faculty_id вже містить "faculty_" префікс
    if not faculty_id.startswith("faculty_"):
        full_faculty_id = f"faculty_{faculty_id}"
    else:
        full_faculty_id = faculty_id
        faculty_id = faculty_id.replace("faculty_", "")
    
    # Зберігаємо факультет в стані (з префіксом)
    await state.update_data(faculty_id=full_faculty_id)
    
    # Отримуємо список спеціальностей
    specialties = get_faculty_specialties_list(full_faculty_id)
    
    if not specialties:
        logger.warning(f"Не знайдено спеціальностей для факультету: {full_faculty_id}")
        await callback.answer("❌ Спеціальності не знайдено", show_alert=True)
        return
    
    # Отримуємо назву факультету
    faculties = get_faculties_list()
    faculty_info = next((f for f in faculties if f['id'] == full_faculty_id), None)
    faculty_name = faculty_info.get('name', full_faculty_id) if faculty_info else full_faculty_id
    
    # Створюємо кнопки зі спеціальностями
    keyboard_buttons = []
    for idx, specialty in enumerate(specialties):
        button_text = specialty[:40] + "..." if len(specialty) > 40 else specialty
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"tuition_manage_spec_{faculty_id}_{idx}"
            )
        ])
    
    keyboard_buttons.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="tuition_back_to_faculties")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await callback.message.edit_text(
        f"💵 <b>Управління вартістю навчання</b>\n\n"
        f"📚 <b>{faculty_name}</b>\n\n"
        f"Оберіть спеціальність:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tuition_manage_spec_"))
async def tuition_manage_spec_handler(callback: CallbackQuery, state: FSMContext):
    """Показ вартості для спеціальності з можливістю редагування"""
    if callback.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await callback.answer("❌ У вас немає доступу", show_alert=True)
        return
    
    try:
        # Формат: tuition_manage_spec_{faculty_id}_{specialty_idx}
        parts = callback.data.replace("tuition_manage_spec_", "").split("_")
        faculty_id = f"faculty_{parts[0]}"
        specialty_idx = int(parts[1])
        
        from knowledge_base import get_faculty_specialties_list
        from tuition_helper import find_tuition_info
        
        specialties = get_faculty_specialties_list(faculty_id)
        
        if not specialties or specialty_idx >= len(specialties):
            await callback.answer("❌ Спеціальність не знайдена", show_alert=True)
            return
        
        specialty_name = specialties[specialty_idx]
        
        # Зберігаємо в стані для подальшого використання
        await state.update_data(
            specialty_name=specialty_name,
            faculty_id=faculty_id
        )
        
        # Перевіряємо, чи є вартість в базі
        from database import db
        
        # Шукаємо всі вартості для цієї спеціальності
        tuition_records = await db.get_tuition_by_specialty_name(specialty_name)
        
        # Формуємо текст відповіді
        text = f"💵 <b>Вартість навчання</b>\n\n"
        text += f"📚 <b>{specialty_name}</b>\n\n"
        
        if tuition_records:
            text += "📊 <b>Поточна вартість:</b>\n\n"
            for record in tuition_records:
                level = record.get('education_level', '').capitalize()
                form = record.get('study_form', '').capitalize()
                monthly = record.get('price_monthly', '')
                semester = record.get('price_semester', '')
                year = record.get('price_year', '')
                price_id = record['id']
                
                text += f"• <b>{level} ({form})</b>\n"
                text += f"  Місяць: {monthly}\n"
                if semester:
                    text += f"  Семестр: {semester}\n"
                if year:
                    text += f"  Рік: {year}\n"
                text += f"  [ID: {price_id}]\n\n"
        else:
            text += "ℹ️ Вартість навчання для цієї спеціальності ще не вказана.\n\n"
        
        # Створюємо кнопки
        keyboard_buttons = []
        
        if tuition_records:
            # Якщо є вартість - показуємо кнопки редагування
            # Групуємо вартості за рівнем та формою для редагування
            seen_combos = set()
            for record in tuition_records:
                level = record.get('education_level', '').lower()
                form = record.get('study_form', '').lower()
                combo = f"{level}_{form}"
                if combo not in seen_combos:
                    seen_combos.add(combo)
                    level_display = level.capitalize()
                    form_display = form.capitalize()
                    button_text = f"✏️ Змінити: {level_display} ({form_display})"
                    keyboard_buttons.append([
                        InlineKeyboardButton(
                            text=button_text,
                            callback_data=f"tuition_edit_{record['id']}"
                        )
                    ])
                    keyboard_buttons.append([
                        InlineKeyboardButton(
                            text=f"🗑️ Видалити: {level_display} ({form_display})",
                            callback_data=f"tuition_confirm_delete_{record['id']}"
                        )
                    ])
            
            keyboard_buttons.append([
                InlineKeyboardButton(text="➕ Додати ще вартість", callback_data="tuition_add_new")
            ])
        else:
            # Якщо немає вартості - показуємо кнопку додавання
            keyboard_buttons.append([
                InlineKeyboardButton(text="➕ Додати вартість", callback_data="tuition_add_new")
            ])
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="⬅️ Назад до спеціальностей", callback_data=f"tuition_manage_faculty_{parts[0]}")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Помилка обробки спеціальності: {e}", exc_info=True)
        await callback.answer("❌ Помилка при обробці", show_alert=True)


@router.callback_query(F.data == "tuition_add_new")
async def tuition_add_new_handler(callback: CallbackQuery, state: FSMContext):
    """Додавання нової вартості для вибраної спеціальності"""
    if callback.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await callback.answer("❌ У вас немає доступу", show_alert=True)
        return
    
    from handlers.menu_handlers import TuitionStates
    
    data = await state.get_data()
    specialty_name = data.get('specialty_name')
    faculty_id = data.get('faculty_id', '')
    
    if not specialty_name:
        await callback.answer("❌ Помилка: спеціальність не вибрана", show_alert=True)
        return
    
    # Знаходимо індекс спеціальності для кнопки "Назад"
    from knowledge_base import get_faculty_specialties_list
    specialties = get_faculty_specialties_list(faculty_id) if faculty_id else []
    try:
        spec_idx = specialties.index(specialty_name) if specialty_name in specialties else 0
    except:
        spec_idx = 0
    
    faculty_id_short = faculty_id.replace('faculty_', '') if faculty_id else ''
    
    # Показуємо вибір рівня освіти
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Бакалавр", callback_data="tuition_level_бакалавр"),
            InlineKeyboardButton(text="Магістр", callback_data="tuition_level_магістр")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"tuition_manage_spec_{faculty_id_short}_{spec_idx}")
        ]
    ])
    
    await callback.message.edit_text(
        f"💵 <b>Додавання вартості навчання</b>\n\n"
        f"📚 Спеціальність: <b>{specialty_name}</b>\n\n"
        f"Оберіть рівень освіти:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    
    # Встановлюємо стан на вибір рівня (пропускаємо вибір факультету та спеціальності)
    await state.set_state(TuitionStates.waiting_for_education_level)
    await callback.answer()


@router.callback_query(F.data.startswith("tuition_edit_"))
async def tuition_edit_handler(callback: CallbackQuery, state: FSMContext):
    """Редагування існуючої вартості"""
    if callback.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await callback.answer("❌ У вас немає доступу", show_alert=True)
        return
    
    try:
        price_id = int(callback.data.replace("tuition_edit_", ""))
        
        # Отримуємо інформацію про вартість
        all_prices = await db.get_all_tuition_prices()
        price = next((p for p in all_prices if p['id'] == price_id), None)
        
        if not price:
            await callback.answer("❌ Вартість не знайдена", show_alert=True)
            return
        
        # Зберігаємо дані в стані для редагування
        await state.update_data(
            editing_price_id=price_id,
            specialty_name=price.get('specialty_name'),
            education_level=price.get('education_level'),
            study_form=price.get('study_form')
        )
        
        specialty = price.get('specialty_name', 'Невідомо')
        level = price.get('education_level', '').capitalize()
        form = price.get('study_form', '').capitalize()
        monthly = price.get('price_monthly', '')
        
        await callback.message.edit_text(
            f"✏️ <b>Редагування вартості</b>\n\n"
            f"📚 <b>{specialty}</b>\n"
            f"🎓 Рівень: <b>{level}</b>\n"
            f"📖 Форма: <b>{form}</b>\n"
            f"💰 Поточна вартість: <b>{monthly}</b>\n\n"
            f"💰 Введіть нову вартість за місяць (тільки число, наприклад: <b>3683</b>):\n"
            f"<i>Система автоматично розрахує вартість за семестр та рік</i>",
            parse_mode="HTML"
        )
        
        from handlers.menu_handlers import TuitionStates
        await state.set_state(TuitionStates.waiting_for_price_monthly)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Помилка редагування вартості: {e}", exc_info=True)
        await callback.answer("❌ Помилка при обробці", show_alert=True)


@router.callback_query(F.data == "tuition_add")
async def tuition_add_handler(callback: CallbackQuery, state: FSMContext):
    """Початок додавання вартості навчання - вибір факультету (legacy, для сумісності)"""
    if callback.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await callback.answer("❌ У вас немає доступу", show_alert=True)
        return
    
    from handlers.menu_handlers import TuitionStates
    from knowledge_base import get_faculties_list
    
    faculties = get_faculties_list()
    
    # Створюємо кнопки з факультетами (по 2 в рядку)
    keyboard_buttons = []
    for i in range(0, len(faculties), 2):
        row = []
        for j in range(i, min(i + 2, len(faculties))):
            faculty = faculties[j]
            button_text = faculty.get('short', faculty.get('name', ''))[:30]
            row.append(InlineKeyboardButton(
                text=button_text,
                callback_data=f"tuition_faculty_{faculty['id']}"
            ))
        keyboard_buttons.append(row)
    
    keyboard_buttons.append([
        InlineKeyboardButton(text="❌ Скасувати", callback_data="tuition_cancel")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await callback.message.edit_text(
        "💵 <b>Додавання вартості навчання</b>\n\n"
        "Оберіть факультет:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(TuitionStates.waiting_for_faculty)
    await callback.answer()


@router.callback_query(F.data.startswith("tuition_confirm_delete_") & ~F.data == "tuition_confirm_delete_all")
async def tuition_confirm_delete_handler(callback: CallbackQuery):
    """Підтвердження видалення окремої вартості"""
    if callback.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await callback.answer("❌ У вас немає доступу", show_alert=True)
        return
    
    try:
        price_id_str = callback.data.replace("tuition_confirm_delete_", "")
        price_id = int(price_id_str)
        
        # Отримуємо інформацію про вартість для підтвердження
        all_prices = await db.get_all_tuition_prices()
        price = next((p for p in all_prices if p['id'] == price_id), None)
        
        if not price:
            await callback.answer("❌ Вартість не знайдена", show_alert=True)
            return
        
        specialty = price.get('specialty_name', 'Невідомо')
        level = price.get('education_level', '').capitalize()
        form = price.get('study_form', '').capitalize()
        monthly = price.get('price_monthly', 'не вказано')
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Так, видалити",
                    callback_data=f"tuition_delete_{price_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Скасувати",
                    callback_data="tuition_list_0"
                )
            ]
        ])
        
        await callback.message.edit_text(
            f"⚠️ <b>Підтвердження видалення</b>\n\n"
            f"Ви дійсно хочете видалити вартість?\n\n"
            f"📚 <b>{specialty}</b>\n"
            f"   {level} ({form}): {monthly}\n\n"
            f"Цю дію неможливо скасувати!",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Помилка підтвердження видалення вартості: {e}", exc_info=True)
        await callback.answer("❌ Помилка при обробці", show_alert=True)


@router.callback_query(F.data.startswith("tuition_delete_") & ~F.data == "tuition_delete_all")
async def tuition_delete_handler(callback: CallbackQuery, state: FSMContext):
    """Видалення окремої вартості (не плутати з tuition_delete_all)"""
    if callback.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await callback.answer("❌ У вас немає доступу", show_alert=True)
        return
    
    try:
        price_id = int(callback.data.replace("tuition_delete_", ""))
        
        # Отримуємо інформацію про вартість перед видаленням
        all_prices = await db.get_all_tuition_prices()
        price = next((p for p in all_prices if p['id'] == price_id), None)
        
        success = await db.delete_tuition_price(price_id)
        
        if success:
            await callback.answer("✅ Вартість видалено")
            
            # Отримуємо дані зі стану для повернення до спеціальності
            data = await state.get_data()
            faculty_id = data.get('faculty_id', '')
            specialty_name = price.get('specialty_name') if price else data.get('specialty_name')
            
            if faculty_id and specialty_name:
                # Повертаємось до перегляду вартості спеціальності
                from knowledge_base import get_faculty_specialties_list
                specialties = get_faculty_specialties_list(faculty_id)
                try:
                    spec_idx = specialties.index(specialty_name) if specialty_name in specialties else 0
                except:
                    spec_idx = 0
                
                faculty_id_short = faculty_id.replace('faculty_', '')
                
                # Викликаємо handler для показу вартості спеціальності
                from aiogram.types import CallbackQuery
                fake_callback = callback
                fake_callback.data = f"tuition_manage_spec_{faculty_id_short}_{spec_idx}"
                await tuition_manage_spec_handler(fake_callback, state)
            else:
                # Якщо немає даних в стані - показуємо просте повідомлення
                await callback.message.edit_text(
                    "✅ <b>Вартість успішно видалено!</b>",
                    parse_mode="HTML"
                )
                # Повертаємось до меню управління вартістю
                from knowledge_base import get_faculties_list
                faculties = get_faculties_list()
                remaining_prices = await db.get_all_tuition_prices()
                
                keyboard_buttons = []
                for i in range(0, len(faculties), 2):
                    row = []
                    for j in range(i, min(i + 2, len(faculties))):
                        faculty = faculties[j]
                        button_text = faculty.get('short', faculty.get('name', ''))[:30]
                        faculty_id_for_callback = faculty['id'].replace('faculty_', '') if faculty['id'].startswith('faculty_') else faculty['id']
                        row.append(InlineKeyboardButton(
                            text=button_text,
                            callback_data=f"tuition_manage_faculty_{faculty_id_for_callback}"
                        ))
                    keyboard_buttons.append(row)
                
                keyboard_buttons.append([
                    InlineKeyboardButton(text="🗑️ Очистити всі вартості", callback_data="tuition_confirm_delete_all")
                ])
                
                await callback.message.answer(
                    "💵 <b>Управління вартістю навчання</b>\n\n"
                    f"📊 <b>Всього записів:</b> {len(remaining_prices)}\n\n"
                    "Оберіть факультет, щоб переглянути або додати вартість:",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons),
                    parse_mode="HTML"
                )
        else:
            await callback.message.edit_text(
                "❌ <b>Помилка при видаленні</b>\n\n"
                "Вартість не була видалена. Можливо, запис вже не існує або сталася помилка.",
                parse_mode="HTML"
            )
            await callback.answer("❌ Помилка при видаленні", show_alert=True)
            
    except ValueError:
        # Якщо не число - це може бути інший callback
        await callback.answer("❌ Невірний формат ID", show_alert=True)
    except Exception as e:
        logger.error(f"Помилка видалення вартості: {e}", exc_info=True)
        await callback.message.edit_text(
            "❌ <b>Помилка при видаленні</b>\n\n"
            f"Сталася помилка: {str(e)}",
            parse_mode="HTML"
        )
        await callback.answer("❌ Помилка при видаленні", show_alert=True)


@router.callback_query(F.data == "tuition_confirm_delete_all")
async def tuition_confirm_delete_all_handler(callback: CallbackQuery):
    """Підтвердження видалення всіх вартостей"""
    if callback.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await callback.answer("❌ У вас немає доступу", show_alert=True)
        return
    
    try:
        all_prices = await db.get_all_tuition_prices()
        total_count = len(all_prices)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Так, очистити все",
                    callback_data="tuition_delete_all"
                ),
                InlineKeyboardButton(
                    text="❌ Скасувати",
                    callback_data="tuition_back_to_faculties"
                )
            ]
        ])
        
        await callback.message.edit_text(
            f"⚠️ <b>Підтвердження очищення</b>\n\n"
            f"Ви дійсно хочете видалити <b>ВСІ</b> вартості навчання?\n\n"
            f"📊 Буде видалено: <b>{total_count}</b> записів\n\n"
            f"⚠️ <b>Цю дію неможливо скасувати!</b>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Помилка підтвердження очищення вартостей: {e}", exc_info=True)
        await callback.answer("❌ Помилка при обробці", show_alert=True)


@router.callback_query(F.data == "tuition_delete_all")
async def tuition_delete_all_handler(callback: CallbackQuery):
    """Видалення всіх вартостей"""
    if callback.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await callback.answer("❌ У вас немає доступу", show_alert=True)
        return
    
    try:
        success = await db.delete_all_tuition_prices()
        
        if success:
            await callback.message.edit_text(
                "✅ <b>Всі вартості успішно видалено!</b>\n\n"
                "База даних очищена.",
                parse_mode="HTML"
            )
            await callback.answer("✅ Всі вартості видалено")
            
            # Повертаємось до меню управління вартістю
            from knowledge_base import get_faculties_list
            faculties = get_faculties_list()
            
            keyboard_buttons = []
            for i in range(0, len(faculties), 2):
                row = []
                for j in range(i, min(i + 2, len(faculties))):
                    faculty = faculties[j]
                    button_text = faculty.get('short', faculty.get('name', ''))[:30]
                    faculty_id_for_callback = faculty['id'].replace('faculty_', '') if faculty['id'].startswith('faculty_') else faculty['id']
                    row.append(InlineKeyboardButton(
                        text=button_text,
                        callback_data=f"tuition_manage_faculty_{faculty_id_for_callback}"
                    ))
                keyboard_buttons.append(row)
            
            keyboard_buttons.append([
                InlineKeyboardButton(text="🗑️ Очистити всі вартості", callback_data="tuition_confirm_delete_all")
            ])
            
            await callback.message.answer(
                "💵 <b>Управління вартістю навчання</b>\n\n"
                "📊 <b>Всього записів:</b> 0\n\n"
                "Оберіть факультет, щоб переглянути або додати вартість:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons),
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                "❌ <b>Помилка при видаленні</b>\n\n"
                "Вартості не були видалені. Можливо, база даних вже порожня або сталася помилка.",
                parse_mode="HTML"
            )
            await callback.answer("❌ Помилка при видаленні", show_alert=True)
            
    except Exception as e:
        logger.error(f"Помилка видалення всіх вартостей: {e}", exc_info=True)
        await callback.message.edit_text(
            "❌ <b>Помилка при видаленні</b>\n\n"
            f"Сталася помилка: {str(e)}",
            parse_mode="HTML"
        )
        await callback.answer("❌ Помилка при видаленні", show_alert=True)

