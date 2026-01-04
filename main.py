import asyncio
import logging
import os
import subprocess
import sys
from dotenv import load_dotenv

# Перезавантажуємо .env на початку
load_dotenv(override=True)

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN, OLLAMA_API_URL, ADMIN_ID
from database import db
from handlers import router
from ollama_client import ollama
from scheduler import start_scheduler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ],
    force=True  # Перезаписуємо існуюче налаштування
)
logger = logging.getLogger(__name__)

# Додаємо handler для всіх модулів
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
if not root_logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    root_logger.addHandler(handler)

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

async def ensure_ollama_running() -> bool:
    logger.info("🔍 Перевірка підключення до OLLAMA...")
    if await ollama.check_health():
        logger.info("✅ OLLAMA доступна")
        return True

    is_docker = False
    if os.path.exists("/.dockerenv"):
        is_docker = True
    elif os.path.exists("/proc/self/cgroup"):
        try:
            with open("/proc/self/cgroup", "r") as f:
                if "docker" in f.read():
                    is_docker = True
        except Exception:
            pass
    
    if is_docker:
        logger.warning("⚠️ OLLAMA недоступна в Docker контейнері!")
        logger.info(f"💡 Перевірте {OLLAMA_API_URL}")
        return False

    logger.warning("⚠️ OLLAMA недоступна! Спробую запустити ollama serve...")
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS

    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )
        await asyncio.sleep(5)
        if await ollama.check_health():
            logger.info("✅ OLLAMA запущено автоматично")
            return True
        logger.warning("⚠️ Не вдалося автоматично запустити OLLAMA. Запустіть вручну: ollama serve")
    except FileNotFoundError:
        logger.error("❌ Команда 'ollama' не знайдена. Встановіть OLLAMA або додайте її до PATH")
    except Exception as e:
        logger.error(f"❌ Помилка запуску OLLAMA: {e}")

    logger.info(f"💡 Перевірте {OLLAMA_API_URL} або запустіть: ollama serve")
    return False

async def main():
    # Перезавантажуємо .env для впевненості
    load_dotenv(override=True)
    
    # Перевіряємо ADMIN_ID напряму з os.getenv
    admin_id_str = os.getenv("ADMIN_ID", "0")
    try:
        admin_id_check = int(admin_id_str.strip()) if admin_id_str and admin_id_str.strip() else 0
    except (ValueError, AttributeError):
        admin_id_check = 0
    
    # Логування ADMIN_ID відразу після завантаження
    logger.info("=" * 60)
    logger.info("🔍 Перевірка налаштувань адміністратора...")
    logger.info(f"📄 ADMIN_ID з os.getenv: '{admin_id_str}'")
    logger.info(f"📦 ADMIN_ID з config: {ADMIN_ID}")
    
    if admin_id_check and admin_id_check != 0:
        logger.info(f"✅ Адміністратор налаштовано: ADMIN_ID = {admin_id_check}")
    else:
        logger.warning("⚠️ ADMIN_ID не встановлено або дорівнює 0")
        logger.info("💡 Перевірте файл .env - має бути: ADMIN_ID=6141597569")
    logger.info("=" * 60)
    
    if not BOT_TOKEN or BOT_TOKEN == "your_bot_token_here":
        logger.error("❌ BOT_TOKEN не встановлено! Перевірте файл .env")
        return
    
    # Перевіряємо OLLAMA, але не зупиняємо бота якщо вона недоступна
    # (бот може працювати з базовими функціями без AI)
    if not await ensure_ollama_running():
        logger.warning("⚠️ OLLAMA недоступна. Бот запуститься з обмеженим функціоналом.")
        logger.info("💡 Для повнофункціональної роботи:")
        logger.info("   1. Запустіть OLLAMA на хост-машині: ollama serve")
        logger.info(f"   2. Перевірте OLLAMA_API_URL в .env: {OLLAMA_API_URL}")
        logger.info("   3. Для Docker використовуйте: http://host.docker.internal:11434")
        # Не зупиняємо бота, він може працювати без AI для базових запитів
    
    try:
        await db.connect()
    except Exception as e:
        logger.warning(f"⚠️ Не вдалося підключитися до БД: {e}")
        logger.info("💡 Бот працюватиме без збереження даних у БД")
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    from middleware.error_handler import ErrorHandlerMiddleware
    from middleware.logging_middleware import LoggingMiddleware
    
    dp.message.middleware(ErrorHandlerMiddleware())
    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(ErrorHandlerMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())
    
    dp.include_router(router)
    start_scheduler()
    
    # Перевірка на дублікати перед запуском
    logger.info("🔍 Перевірка на наявність інших екземплярів...")
    try:
        me = await bot.get_me()
        logger.info(f"✅ Бот підключено: @{me.username} (ID: {me.id})")
    except Exception as e:
        logger.error(f"❌ Не вдалося отримати інформацію про бота: {e}")
        logger.error("💡 Можливо, запущено інший екземпляр або неправильний токен")
        await db.disconnect()
        await bot.session.close()
        return
    
    logger.info("🚀 Бот запущено!")
    
    try:
        # Агресивне видалення webhook перед polling
        try:
            # Спочатку намагаємося видалити webhook кілька разів
            for attempt in range(3):
                try:
                    webhook_info = await bot.get_webhook_info()
                    if webhook_info.url:
                        logger.warning(f"⚠️ Знайдено активний webhook: {webhook_info.url} (спроба {attempt + 1}/3)")
                        await bot.delete_webhook(drop_pending_updates=True)
                        await asyncio.sleep(0.5)  # Невелика затримка між спробами
                    else:
                        logger.info("✅ Webhook не встановлено, використовуємо polling")
                        break
                except Exception as e:
                    if attempt < 2:
                        logger.warning(f"⚠️ Спроба {attempt + 1} не вдалася: {e}, повторюю...")
                        await asyncio.sleep(1)
                    else:
                        logger.error(f"❌ Не вдалося видалити webhook після 3 спроб: {e}")
            
            # Фінальна перевірка
            webhook_info = await bot.get_webhook_info()
            if webhook_info.url:
                logger.error(f"❌ Webhook все ще активний: {webhook_info.url}")
                logger.error("💡 Спробуйте видалити webhook вручну або використайте скрипт stop_all_bots.ps1")
            else:
                logger.info("✅ Webhook успішно видалено")
        except Exception as e:
            logger.warning(f"⚠️ Помилка при перевірці webhook: {e}")
        
        # Додаткова затримка перед запуском polling
        logger.info("⏳ Очікування 2 секунди перед запуском polling...")
        await asyncio.sleep(2)
        
        logger.info("🔄 Запуск polling...")
        await dp.start_polling(
            bot, 
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True,
            close_bot_session=False
        )
    except KeyboardInterrupt:
        logger.info("👋 Бот зупинено користувачем")
    except Exception as e:
        error_msg = str(e)
        # Спеціальна обробка помилки конфлікту
        if "Conflict" in error_msg or "terminated by other getUpdates" in error_msg:
            logger.error("=" * 60)
            logger.error("❌ КОНФЛІКТ: Запущено кілька екземплярів бота!")
            logger.error("=" * 60)
            logger.error("💡 Рішення:")
            logger.error("   1. Перевірте запущені контейнери:")
            logger.error("      docker ps | grep admission_bot")
            logger.error("   2. Зупиніть всі контейнери бота:")
            logger.error("      docker stop admission_bot")
            logger.error("      docker-compose down")
            logger.error("   3. Перевірте чи не запущено бота локально:")
            logger.error("      tasklist | findstr python  (Windows)")
            logger.error("      ps aux | grep main.py     (Linux/Mac)")
            logger.error("   4. Перезапустіть тільки один екземпляр:")
            logger.error("      docker-compose up -d")
            logger.error("=" * 60)
        else:
            logger.error(f"❌ Помилка: {e}", exc_info=True)
    finally:
        await db.disconnect()
        await bot.session.close()
        logger.info("✅ Ресурси звільнено")


async def cleanup_database(days_to_keep: int = 90):
    """Функція для очищення старих даних з БД"""
    logger.info(f"🧹 Запуск очищення БД (збереження даних за останні {days_to_keep} днів)...")
    
    try:
        await db.connect()
    except Exception as e:
        logger.error(f"❌ Помилка підключення до БД: {e}")
        return
    
    logger.info(f"📊 Отримання інформації про розмір БД...")
    db_info = await db.get_database_size()
    
    if db_info:
        logger.info(f"\n📈 Статистика БД:")
        logger.info(f"   Користувачів: {db_info.get('user_count', 0)}")
        logger.info(f"   Повідомлень: {db_info.get('message_count', 0)}")
        logger.info(f"   Метрик: {db_info.get('metrics_count', 0)}")
        logger.info(f"\n📦 Розміри таблиць:")
        for table in db_info.get('table_sizes', [])[:10]:  # Показуємо топ-10
            logger.info(f"   {table['tablename']}: {table['size']}")
    
    logger.info(f"\n🧹 Очищення даних старіших за {days_to_keep} днів...")
    result = await db.cleanup_old_data(days_to_keep)
    
    if result:
        logger.info(f"\n📊 Отримання оновленої інформації про розмір БД...")
        db_info_after = await db.get_database_size()
        
        if db_info_after:
            logger.info(f"\n📈 Оновлена статистика БД:")
            logger.info(f"   Користувачів: {db_info_after.get('user_count', 0)}")
            logger.info(f"   Повідомлень: {db_info_after.get('message_count', 0)}")
            logger.info(f"   Метрик: {db_info_after.get('metrics_count', 0)}")
        
        logger.info(f"\n✅ Очищення завершено успішно!")
    else:
        logger.error(f"\n❌ Помилка під час очищення")
    
    await db.disconnect()


if __name__ == "__main__":
    # Перевіряємо аргументи командного рядка
    if len(sys.argv) > 1 and sys.argv[1] == "cleanup_db":
        # Режим очищення БД
        days_to_keep = 90
        if len(sys.argv) > 2:
            try:
                days_to_keep = int(sys.argv[2])
            except ValueError:
                logger.error(f"❌ Невірний формат кількості днів. Використовується значення за замовчуванням: 90")
        
        try:
            asyncio.run(cleanup_database(days_to_keep))
        except KeyboardInterrupt:
            logger.info("👋 Очищення перервано")
    else:
        # Звичайний режим роботи бота
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            logger.info("👋 Бот зупинено")

