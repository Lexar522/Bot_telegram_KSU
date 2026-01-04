# Скрипт для завантаження версії 1.4 на GitHub

Set-Location "D:\Різне\Bot_telegram_KSU\Bot_V1.4 – копія"

Write-Host "Ініціалізація git репозиторію..." -ForegroundColor Green
git init

Write-Host "Додавання remote репозиторію..." -ForegroundColor Green
git remote add origin https://github.com/Lexar522/Bot_telegram_KSU.git

Write-Host "Додавання файлів..." -ForegroundColor Green
git add .

Write-Host "Створення commit..." -ForegroundColor Green
git commit -m "Version 1.4: Admin panel, DB optimizations, auto academic year"

Write-Host "Створення гілки main..." -ForegroundColor Green
git branch -M main

Write-Host "Завантаження на GitHub..." -ForegroundColor Green
Write-Host "УВАГА: Можливо знадобиться авторизація!" -ForegroundColor Yellow
git push -u origin main

Write-Host "Готово!" -ForegroundColor Green


