@echo off
chcp 65001 >nul
echo ========================================
echo Застосування міграцій БД
echo ========================================
echo.

cd /d "%~dp0"

REM Перевірка чи Docker запущений
docker ps >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Помилка: Docker не запущений або недоступний
    pause
    exit /b 1
)

REM Перевірка чи контейнер БД запущений
docker ps | findstr admission_bot_db >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Помилка: Контейнер БД не запущений
    echo Запустіть: docker-compose up -d postgres
    pause
    exit /b 1
)

echo Застосування міграцій БД...
echo.

docker exec -it admission_bot python -c "import asyncio; from database import Database; async def migrate(): db = Database(); await db.connect(); print('✅ Міграції застосовано'); await db.disconnect(); asyncio.run(migrate())"

if %errorlevel% == 0 (
    echo.
    echo ========================================
    echo ✅ Міграції успішно застосовано!
    echo ========================================
) else (
    echo.
    echo ========================================
    echo ❌ Помилка застосування міграцій
    echo ========================================
    echo Перевірте логи: docker-compose logs bot
)

echo.
pause

