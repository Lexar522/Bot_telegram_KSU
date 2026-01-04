#!/bin/bash

echo "========================================"
echo "Застосування міграцій БД"
echo "========================================"
echo

# Перевірка чи Docker запущений
if ! docker ps > /dev/null 2>&1; then
    echo "❌ Помилка: Docker не запущений або недоступний"
    exit 1
fi

# Перевірка чи контейнер БД запущений
if ! docker ps | grep -q admission_bot_db; then
    echo "❌ Помилка: Контейнер БД не запущений"
    echo "Запустіть: docker-compose up -d postgres"
    exit 1
fi

echo "Застосування міграцій БД..."
echo

docker exec -it admission_bot python -c "
import asyncio
from database import Database

async def migrate():
    db = Database()
    await db.connect()
    print('✅ Міграції застосовано')
    await db.disconnect()

asyncio.run(migrate())
"

if [ $? -eq 0 ]; then
    echo
    echo "========================================"
    echo "✅ Міграції успішно застосовано!"
    echo "========================================"
else
    echo
    echo "========================================"
    echo "❌ Помилка застосування міграцій"
    echo "========================================"
    echo "Перевірте логи: docker-compose logs bot"
    exit 1
fi

echo

