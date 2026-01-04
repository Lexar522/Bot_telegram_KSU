@echo off
:: Запуск через PowerShell для підтримки кирилиці
powershell -ExecutionPolicy Bypass -File "%~dp0run.ps1"
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to run PowerShell script
    echo [INFO] Make sure PowerShell is installed
    pause
    exit /b 1
)
