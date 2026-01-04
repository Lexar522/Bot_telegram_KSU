@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo Виправлення помилки push на GitHub
echo ========================================
echo.

echo Крок 1: Отримання змін з GitHub...
git fetch origin main

echo.
echo Крок 2: Об'єднання змін...
git pull origin main --allow-unrelated-histories --no-edit

if %errorlevel% neq 0 (
    echo.
    echo ⚠️ Помилка при об'єднанні. Спробуємо rebase...
    git pull --rebase origin main
    if %errorlevel% neq 0 (
        echo.
        echo ❌ Не вдалося об'єднати зміни автоматично.
        echo Потрібно вирішити конфлікти вручну.
        echo.
        echo Виконайте:
        echo   git status
        echo   (вирішіть конфлікти)
        echo   git add .
        echo   git commit -m "Resolve conflicts"
        echo   git push -u origin main
        pause
        exit /b 1
    )
)

echo.
echo ✅ Зміни об'єднано успішно

echo.
echo Крок 3: Завантаження на GitHub...
git push -u origin main

if %errorlevel% == 0 (
    echo.
    echo ========================================
    echo ✅ Успішно завантажено на GitHub!
    echo ========================================
) else (
    echo.
    echo ========================================
    echo ❌ Помилка завантаження.
    echo.
    echo Можливі причини:
    echo 1. Потрібна авторизація (логін/пароль або токен)
    echo 2. Є конфлікти, які потрібно вирішити
    echo.
    echo Спробуйте виконати вручну:
    echo   git pull origin main --allow-unrelated-histories
    echo   git push -u origin main
    echo ========================================
)

pause

