import asyncpg
from config import DB_CONFIG

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        try:
            self.pool = await asyncpg.create_pool(**DB_CONFIG, min_size=1, max_size=10)
            await self.create_tables()
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

            print("✅ Таблиці створено/перевірено")

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

    async def delete_reminder(self, reminder_id: int, user_id: int):
        if not self.pool:
            return
        async with self.pool.acquire() as conn:
            await conn.execute("""
                DELETE FROM reminders WHERE id = $1 AND user_id = $2
            """, reminder_id, user_id)


db = Database()

