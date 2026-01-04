import asyncpg
from config import DB_CONFIG

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        try:
            # Оптимізований connection pool для кращої продуктивності
            # min_size=2 - мінімум 2 з'єднання завжди готові
            # max_size=20 - максимум 20 з'єднань (з урахуванням max_connections=50 в PostgreSQL)
            # timeout=30 - таймаут підключення 30 секунд
            # command_timeout=60 - таймаут виконання команди 60 секунд
            self.pool = await asyncpg.create_pool(
                **DB_CONFIG,
                min_size=2,
                max_size=20,
                timeout=30,
                command_timeout=60,
                max_queries=50000,  # Максимум запитів на з'єднання перед переподключенням
                max_inactive_connection_lifetime=300  # 5 хвилин неактивності перед закриттям
            )
            await self.create_tables()
            # Автоматично видаляємо таблицю ai_metrics якщо вона існує (більше не використовується)
            await self._cleanup_ai_metrics_table()
            print("✅ Підключено до бази даних")
        except Exception as e:
            print(f"❌ Помилка підключення до БД: {e}")
            raise

    async def disconnect(self):
        if self.pool:
            await self.pool.close()

    async def create_tables(self):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT UNIQUE NOT NULL,
                    username VARCHAR(255),
                    first_name VARCHAR(255),
                    last_name VARCHAR(255),
                    specialization VARCHAR(255),
                    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS reminders (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
                    deadline_date DATE NOT NULL,
                    deadline_name VARCHAR(255) NOT NULL,
                    is_sent BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    specialization VARCHAR(255),
                    is_required BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS message_history (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
                    user_message TEXT NOT NULL,
                    bot_response TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS response_feedback (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
                    message_history_id INTEGER REFERENCES message_history(id) ON DELETE CASCADE,
                    feedback_type VARCHAR(10) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, message_history_id, feedback_type)
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS shared_contacts (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
                    user_name VARCHAR(255) NOT NULL,
                    phone_number VARCHAR(20),
                    first_name VARCHAR(255),
                    last_name VARCHAR(255),
                    username VARCHAR(255),
                    is_processed BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Додаємо поле is_processed якщо його немає (для існуючих таблиць)
            await conn.execute("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name='shared_contacts' AND column_name='is_processed'
                    ) THEN
                        ALTER TABLE shared_contacts ADD COLUMN is_processed BOOLEAN DEFAULT FALSE;
                    END IF;
                END $$;
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS admin_settings (
                    id SERIAL PRIMARY KEY,
                    admin_id BIGINT UNIQUE NOT NULL,
                    notifications_enabled BOOLEAN DEFAULT TRUE,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_blocks (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
                    blocked_by BIGINT NOT NULL,
                    reason TEXT,
                    blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id)
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS broadcasts (
                    id SERIAL PRIMARY KEY,
                    admin_id BIGINT NOT NULL,
                    message_text TEXT,
                    message_type VARCHAR(20) DEFAULT 'text',
                    file_id VARCHAR(255),
                    send_to_active_only BOOLEAN DEFAULT FALSE,
                    status VARCHAR(20) DEFAULT 'pending',
                    scheduled_at TIMESTAMP,
                    sent_at TIMESTAMP,
                    total_users INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    failed_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS tuition_prices (
                    id SERIAL PRIMARY KEY,
                    specialty_name VARCHAR(255) NOT NULL,
                    specialty_code VARCHAR(50),
                    education_level VARCHAR(50) NOT NULL,
                    study_form VARCHAR(50) NOT NULL,
                    price_monthly VARCHAR(100),
                    price_semester VARCHAR(100),
                    price_year VARCHAR(100),
                    price_total VARCHAR(100),
                    academic_year VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(specialty_name, specialty_code, education_level, study_form)
                )
            """)

            # Створюємо індекси для оптимізації запитів
            await self.create_indexes(conn)
            
            print("✅ Таблиці створено/перевірено")

    async def create_indexes(self, conn):
        """Створення індексів для оптимізації запитів"""
        try:
            # Індекси для message_history (найчастіше використовувана таблиця)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_message_history_user_id 
                ON message_history(user_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_message_history_created_at 
                ON message_history(created_at DESC)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_message_history_user_created 
                ON message_history(user_id, created_at DESC)
            """)
            
            # Індекси для reminders
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_reminders_user_id 
                ON reminders(user_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_reminders_deadline_date 
                ON reminders(deadline_date)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_reminders_user_sent 
                ON reminders(user_id, is_sent)
            """)
            
            # Індекси для users
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_telegram_id 
                ON users(telegram_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_is_active 
                ON users(is_active)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_registration_date 
                ON users(registration_date DESC)
            """)
            
            # Індекси для response_feedback
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_response_feedback_user_id 
                ON response_feedback(user_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_response_feedback_message_history_id 
                ON response_feedback(message_history_id)
            """)
            
            # Індекси для shared_contacts
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_shared_contacts_user_id 
                ON shared_contacts(user_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_shared_contacts_is_processed 
                ON shared_contacts(is_processed)
            """)
            
            # Індекси для user_blocks
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_blocks_user_id 
                ON user_blocks(user_id)
            """)
            
            # Індекси для broadcasts
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_broadcasts_status 
                ON broadcasts(status)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_broadcasts_created_at 
                ON broadcasts(created_at DESC)
            """)
            
            # Індекси для tuition_prices
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tuition_prices_specialty_name 
                ON tuition_prices(LOWER(specialty_name))
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tuition_prices_specialty_code 
                ON tuition_prices(LOWER(specialty_code))
            """)
            
            # Додаткові індекси для оптимізації
            # Індекс для пошуку по даті в message_history (для get_active_users)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_message_history_created_at_date 
                ON message_history(DATE(created_at))
            """)
            
            # Індекс для admin_settings
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_admin_settings_admin_id 
                ON admin_settings(admin_id)
            """)
            
            print("✅ Індекси створено/перевірено")
        except Exception as e:
            print(f"⚠️ Помилка створення індексів: {e}")

    async def _cleanup_ai_metrics_table(self):
        """Видалення таблиці ai_metrics якщо вона існує (більше не використовується)"""
        if not self.pool:
            return
        try:
            async with self.pool.acquire() as conn:
                # Перевіряємо чи існує таблиця
                table_exists = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'ai_metrics'
                    )
                """)
                
                if table_exists:
                    # Видаляємо всі дані
                    await conn.execute("DELETE FROM ai_metrics")
                    # Видаляємо саму таблицю
                    await conn.execute("DROP TABLE IF EXISTS ai_metrics CASCADE")
                    print("✅ Таблиця ai_metrics видалена (більше не використовується)")
        except Exception as e:
            # Не критична помилка
            print(f"ℹ️ Не вдалося видалити ai_metrics: {e}")

    async def register_user(self, telegram_id: int, username: str = None, 
                           first_name: str = None, last_name: str = None):
        if not self.pool:
            return
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO users (telegram_id, username, first_name, last_name)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (telegram_id) 
                DO UPDATE SET 
                    username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    is_active = TRUE
            """, telegram_id, username, first_name, last_name)

    async def get_user(self, telegram_id: int):
        if not self.pool:
            return None
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(
                "SELECT * FROM users WHERE telegram_id = $1", telegram_id
            )

    async def update_specialization(self, telegram_id: int, specialization: str):
        if not self.pool:
            return
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET specialization = $1 WHERE telegram_id = $2",
                specialization, telegram_id
            )

    async def add_reminder(self, telegram_id: int, deadline_date: str, deadline_name: str):
        if not self.pool:
            return
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO reminders (user_id, deadline_date, deadline_name)
                VALUES ($1, $2, $3)
            """, telegram_id, deadline_date, deadline_name)

    async def get_user_reminders(self, telegram_id: int):
        if not self.pool:
            return []
        async with self.pool.acquire() as conn:
            return await conn.fetch(
                "SELECT * FROM reminders WHERE user_id = $1 ORDER BY deadline_date",
                telegram_id
            )

    async def save_message_history(self, telegram_id: int, user_message: str, bot_response: str):
        if not self.pool:
            return None
        async with self.pool.acquire() as conn:
            # Автоматично реєструємо користувача якщо його немає в БД
            # Це запобігає помилкам foreign key constraint
            await conn.execute("""
                INSERT INTO users (telegram_id, is_active)
                VALUES ($1, TRUE)
                ON CONFLICT (telegram_id) DO UPDATE SET is_active = TRUE
            """, telegram_id)
            
            # Тепер зберігаємо повідомлення
            message_id = await conn.fetchval("""
                INSERT INTO message_history (user_id, user_message, bot_response)
                VALUES ($1, $2, $3)
                RETURNING id
            """, telegram_id, user_message, bot_response)
            return message_id

    async def get_recent_messages(self, telegram_id: int, limit: int = 5):
        if not self.pool:
            return []
        async with self.pool.acquire() as conn:
            return await conn.fetch("""
                SELECT user_message, bot_response 
                FROM message_history 
                WHERE user_id = $1 
                ORDER BY created_at DESC 
                LIMIT $2
            """, telegram_id, limit)

    async def save_feedback(self, user_id: int, message_history_id: int, feedback_type: str):
        if not self.pool:
            return
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO response_feedback (user_id, message_history_id, feedback_type)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id, message_history_id, feedback_type) DO NOTHING
            """, user_id, message_history_id, feedback_type)

    async def get_message_history_by_id(self, message_history_id: int):
        if not self.pool:
            return None
        async with self.pool.acquire() as conn:
            return await conn.fetchrow("""
                SELECT user_id, user_message, bot_response
                FROM message_history
                WHERE id = $1
            """, message_history_id)

    async def get_user_stats(self, telegram_id: int):
        if not self.pool:
            return {
                "questions_count": 0,
                "reminders_count": 0,
                "registration_date": None,
                "last_activity": None
            }
        async with self.pool.acquire() as conn:
            questions_count = await conn.fetchval("""
                SELECT COUNT(*) FROM message_history WHERE user_id = $1
            """, telegram_id)
            
            reminders_count = await conn.fetchval("""
                SELECT COUNT(*) FROM reminders WHERE user_id = $1 AND is_sent = FALSE
            """, telegram_id)
            
            registration_date = await conn.fetchval("""
                SELECT registration_date FROM users WHERE telegram_id = $1
            """, telegram_id)
            
            last_activity = await conn.fetchval("""
                SELECT MAX(created_at) FROM message_history WHERE user_id = $1
            """, telegram_id)
            
            return {
                "questions_count": questions_count or 0,
                "reminders_count": reminders_count or 0,
                "registration_date": registration_date,
                "last_activity": last_activity
            }

    async def get_message_history_with_ids(self, telegram_id: int, limit: int = 10):
        if not self.pool:
            return []
        async with self.pool.acquire() as conn:
            return await conn.fetch("""
                SELECT id, user_message, bot_response, created_at
                FROM message_history 
                WHERE user_id = $1 
                ORDER BY created_at DESC 
                LIMIT $2
            """, telegram_id, limit)

    async def delete_reminder(self, reminder_id: int, user_id: int) -> bool:
        """Видалити нагадування. Повертає True якщо видалено, False якщо не знайдено"""
        if not self.pool:
            return False
        try:
            async with self.pool.acquire() as conn:
                # Перевіряємо, чи існує запис
                existing = await conn.fetchrow(
                    "SELECT id FROM reminders WHERE id = $1 AND user_id = $2",
                    reminder_id, user_id
                )
                if not existing:
                    return False
                
                # Видаляємо запис
                result = await conn.execute("""
                    DELETE FROM reminders WHERE id = $1 AND user_id = $2
                """, reminder_id, user_id)
                
                # Перевіряємо результат
                if result and "DELETE" in result and int(result.split()[-1]) > 0:
                    return True
                return False
        except Exception as e:
            print(f"Помилка видалення нагадування: {e}")
            return False
    
    async def delete_all_reminders(self, user_id: int) -> bool:
        """Видалити всі нагадування користувача. Повертає True якщо видалено, False якщо помилка"""
        if not self.pool:
            return False
        try:
            async with self.pool.acquire() as conn:
                # Перевіряємо, чи є записи
                count = await conn.fetchval("SELECT COUNT(*) FROM reminders WHERE user_id = $1", user_id)
                if count == 0:
                    return True  # Немає що видаляти, але це не помилка
                
                # Видаляємо всі записи
                result = await conn.execute("DELETE FROM reminders WHERE user_id = $1", user_id)
                
                # Перевіряємо результат
                if result and "DELETE" in result:
                    deleted_count = int(result.split()[-1])
                    return deleted_count > 0
                return False
        except Exception as e:
            print(f"Помилка видалення всіх нагадувань: {e}")
            return False

    async def save_shared_contact(self, user_id: int, user_name: str, phone_number: str = None,
                                  first_name: str = None, last_name: str = None, username: str = None):
        """Збереження поділеного контакту (якщо ще не збережений). Повертає contact_id або False"""
        if not self.pool:
            return False
        
        # Перевіряємо, чи вже є контакт для цього користувача
        has_contact = await self.has_shared_contact(user_id)
        if has_contact:
            return False  # Контакт вже існує
        
        async with self.pool.acquire() as conn:
            contact_id = await conn.fetchval("""
                INSERT INTO shared_contacts (user_id, user_name, phone_number, first_name, last_name, username)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
            """, user_id, user_name, phone_number, first_name, last_name, username)
        return contact_id  # Повертаємо ID збереженого контакту

    async def get_all_shared_contacts(self, only_unprocessed: bool = False):
        """Отримання всіх поділених контактів для адміна"""
        if not self.pool:
            return []
        async with self.pool.acquire() as conn:
            query = """
                SELECT sc.*, u.username as telegram_username, u.first_name as telegram_first_name
                FROM shared_contacts sc
                LEFT JOIN users u ON sc.user_id = u.telegram_id
            """
            if only_unprocessed:
                query += " WHERE sc.is_processed = FALSE"
            query += " ORDER BY sc.created_at DESC"
            return await conn.fetch(query)
    
    async def get_unprocessed_contacts_count(self):
        """Отримання кількості неопрацьованих контактів"""
        if not self.pool:
            return 0
        async with self.pool.acquire() as conn:
            count = await conn.fetchval("""
                SELECT COUNT(*) FROM shared_contacts WHERE is_processed = FALSE
            """)
            return count or 0
    
    async def mark_contact_as_processed(self, contact_id: int):
        """Відмітити контакт як опрацьований"""
        if not self.pool:
            return False
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE shared_contacts SET is_processed = TRUE WHERE id = $1
            """, contact_id)
            return True
    
    async def mark_contact_as_unprocessed(self, contact_id: int):
        """Відмітити контакт як неопрацьований"""
        if not self.pool:
            return False
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE shared_contacts SET is_processed = FALSE WHERE id = $1
            """, contact_id)
            return True
    
    async def delete_all_contacts(self):
        """Очистити всі контакти"""
        if not self.pool:
            return False
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM shared_contacts")
            return True
    
    async def delete_processed_contacts(self):
        """Очистити тільки опрацьовані контакти"""
        if not self.pool:
            return False
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM shared_contacts WHERE is_processed = TRUE")
            return True
    
    async def delete_contact_by_id(self, contact_id: int):
        """Видалити конкретний контакт за ID"""
        if not self.pool:
            return False
        async with self.pool.acquire() as conn:
            result = await conn.execute("DELETE FROM shared_contacts WHERE id = $1", contact_id)
            return "DELETE" in result  # Повертає True якщо контакт був видалений
    
    async def get_admin_notifications_setting(self, admin_id: int) -> bool:
        """Отримати налаштування сповіщень для адміна"""
        if not self.pool:
            return True  # За замовчуванням увімкнено
        async with self.pool.acquire() as conn:
            setting = await conn.fetchrow("""
                SELECT notifications_enabled FROM admin_settings WHERE admin_id = $1
            """, admin_id)
            if setting:
                return setting['notifications_enabled']
            # Якщо налаштування немає - створюємо з увімкненими сповіщеннями
            await conn.execute("""
                INSERT INTO admin_settings (admin_id, notifications_enabled)
                VALUES ($1, TRUE)
                ON CONFLICT (admin_id) DO NOTHING
            """, admin_id)
            return True
    
    async def set_admin_notifications(self, admin_id: int, enabled: bool):
        """Встановити налаштування сповіщень для адміна"""
        if not self.pool:
            return
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO admin_settings (admin_id, notifications_enabled)
                VALUES ($1, $2)
                ON CONFLICT (admin_id) DO UPDATE SET notifications_enabled = $2, updated_at = CURRENT_TIMESTAMP
            """, admin_id, enabled)
    
    # Методи для роботи з користувачами
    async def get_all_users(self, limit: int = 100, offset: int = 0):
        """Отримати список всіх користувачів"""
        if not self.pool:
            return []
        async with self.pool.acquire() as conn:
            # Оптимізований запит з JOIN замість підзапитів
            users = await conn.fetch("""
                SELECT 
                    u.*,
                    COALESCE(mh_stats.messages_count, 0) as messages_count,
                    mh_stats.last_activity,
                    COALESCE(ub.is_blocked, FALSE) as is_blocked
                FROM users u
                LEFT JOIN (
                    SELECT 
                        user_id,
                        COUNT(*) as messages_count,
                        MAX(created_at) as last_activity
                    FROM message_history
                    GROUP BY user_id
                ) mh_stats ON u.telegram_id = mh_stats.user_id
                LEFT JOIN (
                    SELECT user_id, TRUE as is_blocked
                    FROM user_blocks
                ) ub ON u.telegram_id = ub.user_id
                ORDER BY u.registration_date DESC
                LIMIT $1 OFFSET $2
            """, limit, offset)
            return users
    
    async def search_users(self, query: str, limit: int = 50):
        """Пошук користувачів за ім'ям, username або ID"""
        if not self.pool:
            return []
        async with self.pool.acquire() as conn:
            search_pattern = f"%{query}%"
            # Оптимізований запит з JOIN замість підзапитів
            users = await conn.fetch("""
                SELECT 
                    u.*,
                    COALESCE(mh_stats.messages_count, 0) as messages_count,
                    mh_stats.last_activity,
                    COALESCE(ub.is_blocked, FALSE) as is_blocked
                FROM users u
                LEFT JOIN (
                    SELECT 
                        user_id,
                        COUNT(*) as messages_count,
                        MAX(created_at) as last_activity
                    FROM message_history
                    GROUP BY user_id
                ) mh_stats ON u.telegram_id = mh_stats.user_id
                LEFT JOIN (
                    SELECT user_id, TRUE as is_blocked
                    FROM user_blocks
                ) ub ON u.telegram_id = ub.user_id
                WHERE u.telegram_id::text LIKE $1 
                   OR u.username LIKE $2 
                   OR u.first_name LIKE $2 
                   OR u.last_name LIKE $2
                ORDER BY u.registration_date DESC
                LIMIT $3
            """, query if query.isdigit() else "0", search_pattern, limit)
            return users
    
    async def get_user_by_id(self, user_id: int):
        """Отримати інформацію про користувача за ID з додатковою інформацією"""
        if not self.pool:
            return None
        async with self.pool.acquire() as conn:
            # Оптимізований запит з JOIN замість підзапитів
            user = await conn.fetchrow("""
                SELECT 
                    u.*,
                    COALESCE(mh_stats.messages_count, 0) as messages_count,
                    mh_stats.last_activity,
                    COALESCE(ub.is_blocked, FALSE) as is_blocked
                FROM users u
                LEFT JOIN (
                    SELECT 
                        user_id,
                        COUNT(*) as messages_count,
                        MAX(created_at) as last_activity
                    FROM message_history
                    WHERE user_id = $1
                    GROUP BY user_id
                ) mh_stats ON u.telegram_id = mh_stats.user_id
                LEFT JOIN (
                    SELECT user_id, TRUE as is_blocked
                    FROM user_blocks
                    WHERE user_id = $1
                ) ub ON u.telegram_id = ub.user_id
                WHERE u.telegram_id = $1
            """, user_id)
            return user
    
    async def block_user(self, user_id: int, admin_id: int, reason: str = None):
        """Заблокувати користувача"""
        if not self.pool:
            return False
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO user_blocks (user_id, blocked_by, reason)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id) DO UPDATE SET blocked_by = $2, reason = $3
            """, user_id, admin_id, reason)
            return True
    
    async def unblock_user(self, user_id: int):
        """Розблокувати користувача"""
        if not self.pool:
            return False
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM user_blocks WHERE user_id = $1", user_id)
            return True
    
    async def is_user_blocked(self, user_id: int) -> bool:
        """Перевірити, чи заблокований користувач"""
        if not self.pool:
            return False
        async with self.pool.acquire() as conn:
            count = await conn.fetchval("SELECT COUNT(*) FROM user_blocks WHERE user_id = $1", user_id)
            return count > 0 if count else False
    
    async def get_active_users(self, days: int = 30):
        """Отримати список активних користувачів за останні N днів"""
        if not self.pool:
            return []
        async with self.pool.acquire() as conn:
            # Використовуємо параметризований запит замість f-string для безпеки та продуктивності
            # Використовуємо make_interval для безпечного формування інтервалу
            users = await conn.fetch("""
                SELECT DISTINCT u.telegram_id
                FROM users u
                INNER JOIN message_history mh ON u.telegram_id = mh.user_id
                WHERE mh.created_at >= CURRENT_DATE - make_interval(days => $1)
                  AND NOT EXISTS(SELECT 1 FROM user_blocks WHERE user_id = u.telegram_id)
                ORDER BY u.telegram_id
            """, days)
            return [u['telegram_id'] for u in users]
    
    async def get_all_user_ids(self):
        """Отримати список ID всіх користувачів"""
        if not self.pool:
            return []
        async with self.pool.acquire() as conn:
            users = await conn.fetch("""
                SELECT telegram_id FROM users
                ORDER BY telegram_id
            """)
            return [u['telegram_id'] for u in users]
    
    # Методи для роботи з розсилками
    async def create_broadcast(self, admin_id: int, message_text: str = None, message_type: str = 'text',
                              file_id: str = None, send_to_active_only: bool = False, scheduled_at=None):
        """Створити розсилку"""
        if not self.pool:
            return None
        async with self.pool.acquire() as conn:
            broadcast_id = await conn.fetchval("""
                INSERT INTO broadcasts (admin_id, message_text, message_type, file_id, send_to_active_only, scheduled_at, status)
                VALUES ($1, $2, $3, $4, $5, $6, 'pending')
                RETURNING id
            """, admin_id, message_text, message_type, file_id, send_to_active_only, scheduled_at)
            return broadcast_id
    
    async def update_broadcast_status(self, broadcast_id: int, status: str, success_count: int = 0, failed_count: int = 0):
        """Оновити статус розсилки"""
        if not self.pool:
            return False
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE broadcasts 
                SET status = $1::VARCHAR, success_count = $2, failed_count = $3,
                    sent_at = CASE WHEN $1 = 'sent' THEN CURRENT_TIMESTAMP ELSE sent_at END
                WHERE id = $4
            """, status, success_count, failed_count, broadcast_id)
            return True

    async def has_shared_contact(self, user_id: int) -> bool:
        """Перевірка, чи користувач вже поділився контактом"""
        if not self.pool:
            return False
        try:
            async with self.pool.acquire() as conn:
                count = await conn.fetchval("""
                    SELECT COUNT(*) FROM shared_contacts WHERE user_id = $1
                """, user_id)
                result = count > 0 if count else False
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"has_shared_contact для {user_id}: count={count}, result={result}")
                return result
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Помилка в has_shared_contact для {user_id}: {e}", exc_info=True)
            return False

    async def get_bot_statistics(self):
        """Отримання загальної статистики бота для адміна (оптимізована версія)"""
        if not self.pool:
            return {
                "total_users": 0,
                "active_users": 0,
                "total_messages": 0,
                "total_reminders": 0,
                "total_shared_contacts": 0,
                "users_today": 0,
                "users_week": 0,
                "messages_today": 0,
                "messages_week": 0,
                "last_registration": None,
                "most_active_user": None
            }
        
        async with self.pool.acquire() as conn:
            # Оптимізовано: об'єднуємо кілька запитів в один для зменшення навантаження
            # Основна статистика одним запитом
            basic_stats = await conn.fetchrow("""
                SELECT 
                    (SELECT COUNT(DISTINCT telegram_id) FROM users) as total_users,
                    (SELECT COUNT(DISTINCT telegram_id) FROM users WHERE is_active = TRUE) as active_users,
                    (SELECT COUNT(*) FROM message_history) as total_messages,
                    (SELECT COUNT(*) FROM reminders) as total_reminders,
                    (SELECT COUNT(*) FROM shared_contacts) as total_shared_contacts,
                    (SELECT MAX(registration_date) FROM users) as last_registration,
                    (SELECT COUNT(*) FROM reminders WHERE is_sent = FALSE) as active_reminders,
                    (SELECT COUNT(*) FROM reminders WHERE is_sent = TRUE) as sent_reminders
            """)
            
            # Статистика за сьогодні та тиждень одним запитом
            time_stats = await conn.fetchrow("""
                SELECT 
                    (SELECT COUNT(DISTINCT user_id) FROM message_history WHERE DATE(created_at) = CURRENT_DATE) as users_today,
                    (SELECT COUNT(*) FROM message_history WHERE DATE(created_at) = CURRENT_DATE) as messages_today,
                    (SELECT COUNT(DISTINCT user_id) FROM message_history WHERE created_at >= CURRENT_DATE - INTERVAL '7 days') as users_week,
                    (SELECT COUNT(*) FROM message_history WHERE created_at >= CURRENT_DATE - INTERVAL '7 days') as messages_week
            """)
            
            # Найактивніший користувач
            most_active_user = await conn.fetchrow("""
                SELECT u.telegram_id, u.first_name, u.username, COUNT(mh.id) as message_count
                FROM users u
                LEFT JOIN message_history mh ON u.telegram_id = mh.user_id
                GROUP BY u.telegram_id, u.first_name, u.username
                ORDER BY message_count DESC
                LIMIT 1
            """)
            
            # Статистика по спеціалізаціях
            specializations_stats = await conn.fetch("""
                SELECT specialization, COUNT(*) as count
                FROM users
                WHERE specialization IS NOT NULL
                GROUP BY specialization
                ORDER BY count DESC
                LIMIT 5
            """)
            
            # Статистика по днях (останні 7 днів)
            daily_stats = await conn.fetch("""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as messages_count,
                    COUNT(DISTINCT user_id) as users_count
                FROM message_history
                WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """)
            
            return {
                "total_users": basic_stats['total_users'] or 0,
                "active_users": basic_stats['active_users'] or 0,
                "total_messages": basic_stats['total_messages'] or 0,
                "total_reminders": basic_stats['total_reminders'] or 0,
                "active_reminders": basic_stats['active_reminders'] or 0,
                "sent_reminders": basic_stats['sent_reminders'] or 0,
                "total_shared_contacts": basic_stats['total_shared_contacts'] or 0,
                "users_today": time_stats['users_today'] or 0,
                "users_week": time_stats['users_week'] or 0,
                "messages_today": time_stats['messages_today'] or 0,
                "messages_week": time_stats['messages_week'] or 0,
                "last_registration": basic_stats['last_registration'],
                "most_active_user": dict(most_active_user) if most_active_user else None,
                "specializations_stats": [dict(row) for row in specializations_stats] if specializations_stats else [],
                "daily_stats": [dict(row) for row in daily_stats] if daily_stats else []
            }

    # ==================== МЕТОДИ ДЛЯ РОБОТИ З ВАРТІСТЮ НАВЧАННЯ ====================
    
    async def get_tuition_price(self, specialty_name: str = None, specialty_code: str = None, 
                                 education_level: str = None, study_form: str = None):
        """Отримати вартість навчання для спеціальності"""
        if not self.pool:
            return None
        
        async with self.pool.acquire() as conn:
            query = "SELECT * FROM tuition_prices WHERE 1=1"
            params = []
            param_num = 1
            
            if specialty_name:
                query += f" AND LOWER(specialty_name) LIKE ${param_num}"
                params.append(f"%{specialty_name.lower()}%")
                param_num += 1
            
            if specialty_code:
                query += f" AND LOWER(specialty_code) = ${param_num}"
                params.append(specialty_code.lower())
                param_num += 1
            
            if education_level:
                query += f" AND LOWER(education_level) = ${param_num}"
                params.append(education_level.lower())
                param_num += 1
            
            if study_form:
                query += f" AND LOWER(study_form) = ${param_num}"
                params.append(study_form.lower())
                param_num += 1
            
            rows = await conn.fetch(query, *params)
            
            if rows:
                result = []
                for row in rows:
                    result.append(dict(row))
                return result
            return None
    
    async def get_all_tuition_prices(self):
        """Отримати всі вартості навчання"""
        if not self.pool:
            return []
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM tuition_prices ORDER BY specialty_name, education_level, study_form")
            return [dict(row) for row in rows]
    
    def get_current_academic_year(self) -> str:
        """Автоматично визначає поточний навчальний рік у форматі YYYY-YYYY"""
        from datetime import datetime
        now = datetime.now()
        current_year = now.year
        current_month = now.month
        
        # Навчальний рік починається з вересня (місяць 9)
        # Якщо зараз вересень-грудень: поточний_рік - (поточний_рік+1)
        # Якщо зараз січень-серпень: (поточний_рік-1) - поточний_рік
        if current_month >= 9:
            # Вересень-грудень: 2026-2027
            return f"{current_year}-{current_year + 1}"
        else:
            # Січень-серпень: 2025-2026
            return f"{current_year - 1}-{current_year}"

    async def set_tuition_price(self, specialty_name: str, education_level: str, study_form: str,
                                price_monthly: str = None, price_semester: str = None, 
                                price_year: str = None, price_total: str = None,
                                specialty_code: str = None, academic_year: str = None):
        """Встановити або оновити вартість навчання"""
        if not self.pool:
            return False
        
        # Якщо academic_year не вказано, автоматично встановлюємо поточний навчальний рік
        if academic_year is None:
            academic_year = self.get_current_academic_year()
        
        async with self.pool.acquire() as conn:
            # Перевіряємо чи існує запис
            # Явно вказуємо тип для specialty_code, щоб уникнути помилки з NULL
            if specialty_code:
                existing = await conn.fetchrow("""
                    SELECT id FROM tuition_prices 
                    WHERE LOWER(specialty_name) = LOWER($1) 
                    AND LOWER(education_level) = LOWER($2) 
                    AND LOWER(study_form) = LOWER($3)
                    AND (specialty_code IS NULL OR LOWER(specialty_code) = LOWER($4::VARCHAR))
                """, specialty_name, education_level, study_form, specialty_code)
            else:
                existing = await conn.fetchrow("""
                    SELECT id FROM tuition_prices 
                    WHERE LOWER(specialty_name) = LOWER($1) 
                    AND LOWER(education_level) = LOWER($2) 
                    AND LOWER(study_form) = LOWER($3)
                    AND specialty_code IS NULL
                """, specialty_name, education_level, study_form)
            
            if existing:
                # Оновлюємо
                await conn.execute("""
                    UPDATE tuition_prices 
                    SET price_monthly = COALESCE($1, price_monthly),
                        price_semester = COALESCE($2, price_semester),
                        price_year = COALESCE($3, price_year),
                        price_total = COALESCE($4, price_total),
                        specialty_code = COALESCE($5, specialty_code),
                        academic_year = COALESCE($6, academic_year),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = $7
                """, price_monthly, price_semester, price_year, price_total, specialty_code, academic_year, existing['id'])
            else:
                # Створюємо новий
                await conn.execute("""
                    INSERT INTO tuition_prices 
                    (specialty_name, specialty_code, education_level, study_form, 
                     price_monthly, price_semester, price_year, price_total, academic_year)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """, specialty_name, specialty_code, education_level, study_form,
                    price_monthly, price_semester, price_year, price_total, academic_year)
            
            return True
    
    async def delete_tuition_price(self, price_id: int):
        """Видалити вартість навчання"""
        if not self.pool:
            return False
        
        try:
            async with self.pool.acquire() as conn:
                # Перевіряємо, чи існує запис перед видаленням
                existing = await conn.fetchrow("SELECT id FROM tuition_prices WHERE id = $1", price_id)
                if not existing:
                    return False
                
                # Видаляємо запис
                result = await conn.execute("DELETE FROM tuition_prices WHERE id = $1", price_id)
                
                # Перевіряємо результат (asyncpg повертає рядок типу "DELETE 1")
                if result and "DELETE" in result and int(result.split()[-1]) > 0:
                    return True
                return False
        except Exception as e:
            print(f"Помилка видалення вартості: {e}")
            return False
    
    async def delete_all_tuition_prices(self):
        """Видалити всі вартості навчання"""
        if not self.pool:
            return False
        
        try:
            async with self.pool.acquire() as conn:
                # Перевіряємо, чи є записи перед видаленням
                count = await conn.fetchval("SELECT COUNT(*) FROM tuition_prices")
                if count == 0:
                    return True  # Немає що видаляти, але це не помилка
                
                # Видаляємо всі записи
                result = await conn.execute("DELETE FROM tuition_prices")
                
                # Перевіряємо результат
                if result and "DELETE" in result:
                    deleted_count = int(result.split()[-1])
                    return deleted_count > 0
                return False
        except Exception as e:
            print(f"Помилка видалення всіх вартостей: {e}")
            return False
    
    async def get_tuition_by_specialty_name(self, specialty_name: str):
        """Отримати всі вартості для спеціальності за назвою"""
        if not self.pool:
            return []
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM tuition_prices 
                WHERE LOWER(specialty_name) LIKE LOWER($1)
                ORDER BY education_level, study_form
            """, f"%{specialty_name}%")
            return [dict(row) for row in rows]

    async def cleanup_old_data(self, days_to_keep: int = 90):
        """Очищення старих даних для зменшення розміру БД"""
        if not self.pool:
            return False
        
        try:
            async with self.pool.acquire() as conn:
                # Використовуємо параметризовані запити замість f-string для безпеки
                days_param = str(days_to_keep)
                
                # Видаляємо старі записи з message_history (старіше за days_to_keep днів)
                deleted_messages = await conn.execute("""
                    DELETE FROM message_history 
                    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL $1 || ' days'
                """, days_param)
                
                # Видаляємо ВСІ записи з ai_metrics (таблиця більше не використовується)
                # Це вже робиться при старті в _cleanup_ai_metrics_table, але для впевненості
                try:
                    table_exists = await conn.fetchval("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = 'ai_metrics'
                        )
                    """)
                    
                    if table_exists:
                        await conn.execute("DELETE FROM ai_metrics")
                        print(f"✅ Видалено всі записи з ai_metrics")
                except Exception as e:
                    # Таблиця може не існувати, це нормально
                    pass
                
                # Видаляємо старі опрацьовані нагадування (старіше за days_to_keep днів)
                deleted_reminders = await conn.execute("""
                    DELETE FROM reminders 
                    WHERE is_sent = TRUE 
                    AND created_at < CURRENT_TIMESTAMP - INTERVAL $1 || ' days'
                """, days_param)
                
                # Виконуємо VACUUM для оптимізації БД
                await conn.execute("VACUUM ANALYZE")
                
                print(f"✅ Очищено старі дані (старіше {days_to_keep} днів)")
                return True
        except Exception as e:
            print(f"❌ Помилка очищення старих даних: {e}")
            return False

    async def get_database_size(self):
        """Отримати інформацію про розмір БД"""
        if not self.pool:
            return {}
        
        try:
            async with self.pool.acquire() as conn:
                # Розмір таблиць
                table_sizes = await conn.fetch("""
                    SELECT 
                        schemaname,
                        tablename,
                        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
                        pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes
                    FROM pg_tables
                    WHERE schemaname = 'public'
                    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                """)
                
                # Кількість записів в основних таблицях
                message_count = await conn.fetchval("SELECT COUNT(*) FROM message_history")
                user_count = await conn.fetchval("SELECT COUNT(*) FROM users")
                
                # Перевіряємо чи існує таблиця ai_metrics
                metrics_count = 0
                try:
                    metrics_count = await conn.fetchval("SELECT COUNT(*) FROM ai_metrics")
                except Exception:
                    pass
                
                return {
                    "table_sizes": [dict(row) for row in table_sizes],
                    "message_count": message_count or 0,
                    "user_count": user_count or 0,
                    "metrics_count": metrics_count
                }
        except Exception as e:
            print(f"❌ Помилка отримання розміру БД: {e}")
            return {}


db = Database()

