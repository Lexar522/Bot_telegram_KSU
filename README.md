# 🤖 Telegram-бот для абітурієнтів ХДУ

Бот допомагає абітурієнтам отримувати інформацію про вступ, документи, вартість навчання та відповіді на питання.

## 🚀 Швидкий запуск

### Варіант 1: Docker (найпростіше)

**1. Встановіть Docker Desktop:**
- Windows/Mac: https://www.docker.com/products/docker-desktop
- Linux: `sudo apt-get install docker.io docker-compose`

**2. Встановіть OLLAMA:**
- Завантажте: https://ollama.ai/download
- Запустіть: `ollama serve`
- Завантажте модель: `ollama pull llama3.2`

**3. Створіть файл `.env`:**
```env
BOT_TOKEN=ваш_токен_від_BotFather
ADMIN_ID=ваш_telegram_id
OLLAMA_API_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.2
```

**4. Запустіть:**
```bash
docker-compose up -d --build
docker-compose logs -f bot
```

### Варіант 2: Локально (Windows)

**1. Встановіть Python 3.10+** з https://www.python.org/downloads/

**2. Встановіть PostgreSQL:**
- Завантажте: https://www.postgresql.org/download/
- Створіть базу: `CREATE DATABASE admission_bot;`

**3. Встановіть OLLAMA:**
- Завантажте: https://ollama.ai/download
- Запустіть: `ollama serve`
- Завантажте модель: `ollama pull llama3.2`

**4. Створіть `.env` файл:**
```env
BOT_TOKEN=ваш_токен_від_BotFather
ADMIN_ID=ваш_telegram_id
OLLAMA_API_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
DB_HOST=localhost
DB_PORT=5432
DB_NAME=admission_bot
DB_USER=postgres
DB_PASSWORD=ваш_пароль
```

**5. Встановіть залежності:**
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**6. Ініціалізуйте БД:**
```bash
python init_db.py
```

**7. Запустіть:**
```bash
run.bat
```

## 📝 Як отримати BOT_TOKEN

1. Відкрийте Telegram
2. Знайдіть [@BotFather](https://t.me/BotFather)
3. Надішліть `/newbot`
4. Слідуйте інструкціям
5. Скопіюйте токен в `.env`

## 📝 Як отримати ADMIN_ID

1. Відкрийте Telegram
2. Знайдіть [@userinfobot](https://t.me/userinfobot)
3. Надішліть `/start`
4. Скопіюйте свій ID (число) в `.env`

## ✅ Що відбувається при запуску

- Автоматично створюються таблиці в БД
- Запускається планувальник нагадувань
- Бот готовий приймати повідомлення

## 🛑 Зупинка

**Docker:**
```bash
docker-compose down
```

**Локально:**
Натисніть `Ctrl+C` в терміналі

## ❓ Проблеми?

**Бот не запускається:**
- Перевірте файл `.env` (особливо `BOT_TOKEN`)
- Перевірте чи OLLAMA запущена: `ollama list`
- Перегляньте логи: `docker-compose logs bot` (Docker) або логи в консолі (локально)

**OLLAMA недоступна:**
- Запустіть: `ollama serve`
- Перевірте: `ollama list`

**База даних не підключається:**
- Перевірте чи PostgreSQL запущений
- Перевірте налаштування в `.env`

## 🛠 Технології

- Python 3.10+, aiogram 3.4.1, OLLAMA, PostgreSQL, Docker

## 📁 Структура проекту

```
Bot_V1.3/
│
├── 📄 Основні файли
│   ├── main.py                  # Точка входу, запуск бота
│   ├── config.py                # Конфігурація (токени, URLs, DB)
│   ├── database.py              # Робота з PostgreSQL
│   ├── scheduler.py             # Планувальник нагадувань (APScheduler)
│   ├── init_db.py               # Ініціалізація БД з початковими даними
│   ├── keyboards.py             # Клавіатури Telegram
│   ├── knowledge_base.py        # База знань про університет
│   ├── ollama_client.py         # Клієнт OLLAMA (обгортка)
│   └── tuition_helper.py        # Допоміжний модуль для вартості навчання
│
├── 📂 handlers/                 # Обробники подій Telegram
│   ├── __init__.py              # Ініціалізація routers
│   ├── commands.py              # Команди (/start, /help, /stats)
│   ├── chat_handler.py          # Обробка AI-чату з OLLAMA
│   ├── menu_handlers.py         # Обробка кнопок меню
│   ├── reminders.py             # Нагадування про дедлайни
│   ├── settings.py              # Налаштування користувача
│   ├── callbacks.py             # Inline callbacks (кнопки)
│   └── utils.py                 # Допоміжні функції для handlers
│
├── 📂 middleware/               # Middleware для aiogram
│   ├── __init__.py
│   ├── error_handler.py         # Обробка помилок глобально
│   └── logging_middleware.py    # Логування запитів користувачів
│
├── 📂 services/                 # Бізнес-логіка
│   ├── __init__.py
│   ├── knowledge_service.py     # Робота з базою знань
│   └── response_service.py      # Генерація відповідей
│
├── 📂 ollama_optimized/         # Оптимізований OLLAMA клієнт
│   ├── __init__.py
│   ├── client.py                # Основний оптимізований клієнт
│   ├── prompt_builder.py        # Побудова промптів
│   ├── context_optimizer.py     # Оптимізація контексту
│   ├── question_classifier.py   # Класифікація питань
│   ├── cache.py                 # Кешування відповідей
│   ├── semantic_cache.py        # Семантичне кешування
│   ├── validators/              # Валідатори відповідей
│   │   ├── __init__.py
│   │   └── multi_level.py       # Багаторівнева валідація
│   └── metrics/                 # Метрики та статистика
│       ├── __init__.py
│       └── collector.py         # Збір статистики
│
├── 📂 models/                   # Моделі даних
│   ├── __init__.py
│   └── message.py               # Модель повідомлення
│
├── 📂 utils/                    # Утиліти
│   ├── __init__.py
│   ├── message_parser.py        # Парсинг повідомлень
│   └── text_formatter.py        # Форматування тексту
│
├── 📂 validators/               # Валідатори
│   ├── __init__.py
│   ├── content_validator.py     # Валідація контенту
│   └── response_validator.py    # Валідація відповідей
│
├── 📂 ollama_models/            # Локальні OLLAMA моделі (не в Git)
│   └── .gitkeep                 # Для збереження структури
│
├── 📂 university_files/         # Файли університету (PDF, DOCX) (не в Git)
│   └── .gitkeep                 # Для збереження структури
│
├── 📂 reports/                  # Логи помилок (не в Git)
│   └── error_reports.log        # Приватний файл з логами
│
├── 🐳 Docker
│   ├── Dockerfile               # Docker образ бота
│   ├── docker-compose.yml       # Docker Compose конфігурація
│   └── .dockerignore            # Файли для виключення з Docker build
│
├── ⚙️ Конфігурація
│   ├── .env                     # Приватний файл з токенами (НЕ В GIT!)
│   ├── .gitignore               # Правила ігнорування файлів
│   └── requirements.txt         # Python залежності
│
├── 🚀 Скрипти запуску
│   ├── run.bat                  # Скрипт запуску (Windows)
│   └── run.ps1                  # PowerShell скрипт запуску
│
└── 📚 Документація
    └── README.md                # Цей файл
```

### 📝 Важливі зауваження

- **`.env`** - НЕ закомічений в Git (містить приватні токени)
- **`reports/`** - Логи з помилками (НЕ в Git, містить дані користувачів)
- **`university_files/`** - Документи університету (НЕ в Git)
- **`ollama_models/`** - Локальні моделі OLLAMA (НЕ в Git)

## 📝 Ліцензія

Навчальний проект студента 12-243 Чорней О. А.
