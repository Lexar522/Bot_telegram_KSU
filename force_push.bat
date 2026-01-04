@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo УВАГА: Force Push на GitHub
echo ========================================
echo.
echo Цей скрипт ПЕРЕЗАПИШЕ всі файли на GitHub!
echo Всі зміни на GitHub будуть ВТРАЧЕНІ!
echo.
echo Використовуйте тільки якщо:
echo - Ви впевнені, що локальна версія правильна
echo - Ви не втратите важливі дані
echo.
set /p confirm="Продовжити? (yes/no): "
if /i not "%confirm%"=="yes" (
    echo Скасовано.
    pause
    exit /b 0
)

echo.
echo Виконання force push...
git push -f origin main

if %errorlevel% == 0 (
    echo.
    echo ========================================
    echo ✅ Успішно завантажено на GitHub!
    echo ========================================
) else (
    echo.
    echo ========================================
    echo ❌ Помилка завантаження.
    echo ========================================
)

pause

