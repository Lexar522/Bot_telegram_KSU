@echo off
chcp 65001 >nul
cd /d "D:\Різне\Bot_telegram_KSU\Bot_V1.4 – копія"

echo Ініціалізація git репозиторію...
git init

echo Додавання remote репозиторію...
git remote add origin https://github.com/Lexar522/Bot_telegram_KSU.git

echo Додавання файлів...
git add .

echo Створення commit...
git commit -m "Version 1.4: Admin panel, DB optimizations, auto academic year"

echo Створення гілки main...
git branch -M main

echo Завантаження на GitHub...
echo УВАГА: Можливо знадобиться авторизація!
git push -u origin main

echo Готово!
pause

