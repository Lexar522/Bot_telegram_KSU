@echo off
chcp 65001 >nul
cd /d "D:\Різне\Bot_telegram_KSU\Bot_V1.4 – копія"

echo Ініціалізація git репозиторію...
if exist .git (
    echo Git репозиторій вже ініціалізовано
) else (
    git init
)

echo Додавання remote репозиторію...
git remote remove origin 2>nul
git remote add origin https://github.com/Lexar522/Bot_telegram_KSU.git

echo Очищення індексу від непотрібних файлів...
git rm -r --cached . 2>nul

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
git commit -m "Version 1.4: Admin panel, DB optimizations, auto academic year"

echo Створення гілки main...
git branch -M main

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
    echo ========================================
)

pause

