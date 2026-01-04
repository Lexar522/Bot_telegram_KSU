@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo Додавання файлів в GitHub
echo ========================================
echo.

REM Видалення старого репозиторію якщо він є
if exist .git (
    echo Видалення старого репозиторію...
    rmdir /s /q .git
)

echo Ініціалізація git репозиторію...
git init

echo Додавання remote репозиторію...
git remote remove origin 2>nul
git remote add origin https://github.com/Lexar522/Bot_telegram_KSU.git

echo Додавання файлів (з урахуванням .gitignore)...
git add .

echo Перевірка що .env не додано...
git status | findstr /C:".env" >nul
if %errorlevel% == 0 (
    echo УВАГА: .env файл знайдено! Перевірте .gitignore
    pause
    exit /b 1
)

echo Створення commit...
git commit -m "Version 1.4: Admin panel, DB optimizations, Docker update guide, auto academic year"

echo Створення гілки main...
git branch -M main

echo Отримання змін з GitHub (якщо є)...
git pull origin main --allow-unrelated-histories --no-edit
if %errorlevel% neq 0 (
    echo Попередження: Не вдалося отримати зміни (можливо репозиторій порожній)
)

echo Завантаження на GitHub...
echo УВАГА: Можливо знадобиться авторизація!
git push -u origin main

if %errorlevel% == 0 (
    echo.
    echo ========================================
    echo Успішно завантажено на GitHub!
    echo ========================================
) else (
    echo.
    echo ========================================
    echo Помилка завантаження. Перевірте авторизацію.
    echo Можливо потрібно ввести логін та пароль.
    echo ========================================
)

pause

