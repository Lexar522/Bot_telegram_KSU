#!/bin/bash

echo "========================================"
echo "Оновлення проекту в Docker"
echo "========================================"
echo

# Перевірка чи Docker запущений
if ! docker ps > /dev/null 2>&1; then
    echo "❌ Помилка: Docker не запущений або недоступний"
    exit 1
fi

# Створення резервної копії БД
echo "[1/6] Створення резервної копії БД..."
backup_file="backup_$(date +%Y%m%d_%H%M%S).sql"
if docker exec admission_bot_db pg_dump -U postgres admission_bot > "$backup_file" 2>/dev/null; then
    echo "✅ Резервна копія створена: $backup_file"
else
    echo "⚠️ Не вдалося створити резервну копію (можливо БД не запущена)"
fi
echo

# Зупинка бота
echo "[2/6] Зупинка бота..."
if docker-compose stop bot; then
    echo "✅ Бот зупинено"
else
    echo "⚠️ Не вдалося зупинити бота (можливо він не запущений)"
fi
echo

# Перебудова Docker образу
echo "[3/6] Перебудова Docker образу..."
if ! docker-compose build bot; then
    echo "❌ Помилка перебудови образу"
    exit 1
fi
echo "✅ Образ перебудовано"
echo

# Запуск оновленого бота
echo "[4/6] Запуск оновленого бота..."
if ! docker-compose up -d bot; then
    echo "❌ Помилка запуску бота"
    exit 1
fi
echo "✅ Бот запущено"
echo

# Очікування запуску
echo "[5/6] Очікування запуску (10 секунд)..."
sleep 10

# Перевірка логів
echo "[6/6] Перевірка логів..."
echo
echo "Останні 20 рядків логів:"
echo "========================================"
docker-compose logs --tail=20 bot
echo "========================================"
echo

echo "========================================"
echo "✅ Оновлення завершено!"
echo "========================================"
echo
echo "Для перегляду логів у реальному часі виконайте:"
echo "  docker-compose logs -f bot"
echo
echo "Для очищення старих даних (опціонально):"
echo "  docker exec -it admission_bot python main.py cleanup_db 30"
echo

