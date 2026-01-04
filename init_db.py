"""
Скрипт для ініціалізації бази даних з початковими даними
"""
import asyncio
from database import db
from datetime import date, timedelta


async def init_database():
    """Ініціалізація бази даних з початковими даними"""
    await db.connect()
    
    async with db.pool.acquire() as conn:
        # Додаємо приклад документів
        documents = [
            ("Заява", "Заява на вступ (за встановленою формою)", None, True),
            ("Документ про освіту", "Оригінал або копія документа про освіту", None, True),
            ("Додаток до документа про освіту", "Додаток з оцінками", None, True),
            ("Фото", "Фотографії 3x4 (4 штуки)", None, True),
            ("Копія паспорта", "Копія першої та другої сторінки паспорта", None, True),
            ("Копія ідентифікаційного коду", "Копія ІПН", None, True),
            ("Медична довідка", "Форма 086-о", None, True),
            ("Сертифікат ЗНО", "Результати зовнішнього незалежного оцінювання", None, True),
        ]
        
        for doc_name, doc_desc, specialization, is_required in documents:
            await conn.execute("""
                INSERT INTO documents (name, description, specialization, is_required)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT DO NOTHING
            """, doc_name, doc_desc, specialization, is_required)
        
        print("✅ Початкові дані додано до бази даних")
    
    await db.disconnect()


if __name__ == "__main__":
    asyncio.run(init_database())



