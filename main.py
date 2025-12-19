import asyncio
import logging
import os
import subprocess
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN, OLLAMA_API_URL
from database import db
from handlers import router
from ollama_client import ollama
from scheduler import start_scheduler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
    if not BOT_TOKEN or BOT_TOKEN == "your_bot_token_here":
        logger.error("❌ BOT_TOKEN не встановлено! Перевірте файл .env")
        return
    
    if not await ensure_ollama_running():
        logger.error("❌ OLLAMA недоступна. Бот зупинено, запустіть ollama serve та повторіть.")
        return
    
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
    
    logger.info("🚀 Бот запущено!")
    
    try:
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            logger.info("✅ Webhook видалено")
        except Exception as e:
            logger.warning(f"⚠️ Не вдалося видалити webhook: {e}")
        
        await dp.start_polling(
            bot, 
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True,
            close_bot_session=False
        )
    except KeyboardInterrupt:
        logger.info("👋 Бот зупинено користувачем")
    except Exception as e:
        logger.error(f"❌ Помилка: {e}", exc_info=True)
    finally:
        await db.disconnect()
        await bot.session.close()
        logger.info("✅ Ресурси звільнено")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот зупинено")

