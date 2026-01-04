@echo off
chcp 65001 >nul
echo ========================================
echo Оновлення проекту в Docker
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

echo [1/6] Створення резервної копії БД...
set "backup_file=backup_%date:~-4,4%%date:~-7,2%%date:~-10,2%_%time:~0,2%%time:~3,2%%time:~6,2%.sql"
set "backup_file=%backup_file: =0%"
docker exec admission_bot_db pg_dump -U postgres admission_bot > "%backup_file%" 2>nul
if %errorlevel% == 0 (
    echo ✅ Резервна копія створена: %backup_file%
) else (
    echo ⚠️ Не вдалося створити резервну копію (можливо БД не запущена)
)
echo.

echo [2/6] Зупинка бота...
docker-compose stop bot
if %errorlevel% == 0 (
    echo ✅ Бот зупинено
) else (
    echo ⚠️ Не вдалося зупинити бота (можливо він не запущений)
)
echo.

echo [3/6] Перебудова Docker образу...
docker-compose build bot
if %errorlevel% neq 0 (
    echo ❌ Помилка перебудови образу
    pause
    exit /b 1
)
echo ✅ Образ перебудовано
echo.

echo [4/6] Запуск оновленого бота...
docker-compose up -d bot
if %errorlevel% neq 0 (
    echo ❌ Помилка запуску бота
    pause
    exit /b 1
)
echo ✅ Бот запущено
echo.

echo [5/6] Очікування запуску (10 секунд)...
timeout /t 10 /nobreak >nul

echo [6/6] Перевірка логів...
echo.
echo Останні 20 рядків логів:
echo ========================================
docker-compose logs --tail=20 bot
echo ========================================
echo.

echo ========================================
echo ✅ Оновлення завершено!
echo ========================================
echo.
echo Для перегляду логів у реальному часі виконайте:
echo   docker-compose logs -f bot
echo.
echo Для очищення старих даних (опціонально):
echo   docker exec -it admission_bot python main.py cleanup_db 30
echo.
pause

