"""
Простий тест для перевірки роботи оптимізованого OLLAMA клієнта
"""
import asyncio
from ollama_optimized.client import OptimizedOllamaClient
from ollama_optimized.question_classifier import QuestionClassifier
from ollama_optimized.cache import ResponseCache


async def test_question_classifier():
    """Тест класифікації питань"""
    print("🧪 Тестування класифікації питань...")
    classifier = QuestionClassifier()
    
    test_cases = [
        ("Які є факультети?", "faculties"),
        ("Скільки коштує навчання?", "tuition"),
        ("Як вступити?", "procedural"),
        ("Правила вступу 2026", "admission"),
        ("Порівняй бакалавр та магістр", "comparison"),
        ("Що таке ХДУ?", "factual")
    ]
    
    for query, expected_type in test_cases:
        result = classifier.classify(query)
        status = "✅" if result == expected_type else "❌"
        print(f"  {status} '{query}' -> {result} (очікувалось: {expected_type})")


async def test_cache():
    """Тест кешування"""
    print("\n🧪 Тестування кешування...")
    cache = ResponseCache(max_size=10)
    
    query = "Які є факультети?"
    context = {"faculties": {"1": "Факультет 1"}}
    response = "В ХДУ є 8 факультетів..."
    
    # Зберігаємо
    cache.set(query, context, response)
    
    # Отримуємо
    cached = cache.get(query, context)
    
    if cached == response:
        print("  ✅ Кеш працює правильно")
    else:
        print(f"  ❌ Кеш не працює. Отримано: {cached}")
    
    # Статистика
    stats = cache.get_stats()
    print(f"  📊 Статистика кешу: {stats['size']}/{stats['max_size']} ({stats['usage_percent']:.1f}%)")


async def test_client_basic():
    """Базовий тест клієнта"""
    print("\n🧪 Тестування базової роботи клієнта...")
    
    try:
        client = OptimizedOllamaClient()
        
        # Перевірка здоров'я
        is_healthy = await client.check_health()
        if is_healthy:
            print("  ✅ OLLAMA доступна")
        else:
            print("  ⚠️ OLLAMA недоступна - пропускаємо тест генерації")
            return
        
        # Простий тест генерації
        print("  🔄 Генерація відповіді...")
        response = await client.generate_response("Які є факультети в ХДУ?")
        
        if response and len(response) > 10:
            print(f"  ✅ Отримано відповідь ({len(response)} символів)")
            print(f"     Прев'ю: {response[:100]}...")
        else:
            print(f"  ❌ Отримано порожню або занадто коротку відповідь")
        
        # Статистика
        stats = client.get_statistics()
        print(f"  📊 Статистика:")
        print(f"     - Запитів: {stats.get('total_requests', 0)}")
        print(f"     - Cache hit rate: {stats.get('cache_hit_rate', 0):.1f}%")
        print(f"     - Середній час: {stats.get('avg_response_time', 0):.2f}s")
        
    except Exception as e:
        print(f"  ❌ Помилка: {e}")


async def main():
    """Головна функція тестування"""
    print("🚀 Тестування оптимізованого OLLAMA клієнта\n")
    
    # Тест 1: Класифікація
    await test_question_classifier()
    
    # Тест 2: Кешування
    await test_cache()
    
    # Тест 3: Базовий клієнт
    await test_client_basic()
    
    print("\n✅ Тестування завершено!")


if __name__ == "__main__":
    asyncio.run(main())

