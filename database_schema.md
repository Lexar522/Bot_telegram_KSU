# Схема бази даних Telegram-бота для абітурієнтів ХДУ

```mermaid
erDiagram
    users ||--o{ reminders : "має"
    users ||--o{ message_history : "створює"
    users ||--o{ response_feedback : "оцінює"
    users ||--o{ shared_contacts : "поділяє"
    users ||--o| user_blocks : "може бути заблокований"
    users ||--o{ broadcasts : "отримує"
    
    message_history ||--o{ response_feedback : "має відгуки"
    
    admin_settings ||--o{ broadcasts : "створює"
    
    users {
        SERIAL id PK
        BIGINT telegram_id UK "UNIQUE"
        VARCHAR username
        VARCHAR first_name
        VARCHAR last_name
        VARCHAR specialization
        TIMESTAMP registration_date "DEFAULT CURRENT_TIMESTAMP"
        BOOLEAN is_active "DEFAULT TRUE"
    }
    
    reminders {
        SERIAL id PK
        BIGINT user_id FK "REFERENCES users(telegram_id)"
        DATE deadline_date "NOT NULL"
        VARCHAR deadline_name "NOT NULL"
        BOOLEAN is_sent "DEFAULT FALSE"
        TIMESTAMP created_at "DEFAULT CURRENT_TIMESTAMP"
    }
    
    documents {
        SERIAL id PK
        VARCHAR name "NOT NULL"
        TEXT description
        VARCHAR specialization
        BOOLEAN is_required "DEFAULT TRUE"
        TIMESTAMP created_at "DEFAULT CURRENT_TIMESTAMP"
    }
    
    message_history {
        SERIAL id PK
        BIGINT user_id FK "REFERENCES users(telegram_id)"
        TEXT user_message "NOT NULL"
        TEXT bot_response "NOT NULL"
        TIMESTAMP created_at "DEFAULT CURRENT_TIMESTAMP"
    }
    
    response_feedback {
        SERIAL id PK
        BIGINT user_id FK "REFERENCES users(telegram_id)"
        INTEGER message_history_id FK "REFERENCES message_history(id)"
        VARCHAR feedback_type "NOT NULL"
        TIMESTAMP created_at "DEFAULT CURRENT_TIMESTAMP"
        UNIQUE "user_id, message_history_id, feedback_type"
    }
    
    shared_contacts {
        SERIAL id PK
        BIGINT user_id FK "REFERENCES users(telegram_id)"
        VARCHAR user_name "NOT NULL"
        VARCHAR phone_number
        VARCHAR first_name
        VARCHAR last_name
        VARCHAR username
        BOOLEAN is_processed "DEFAULT FALSE"
        TIMESTAMP created_at "DEFAULT CURRENT_TIMESTAMP"
    }
    
    admin_settings {
        SERIAL id PK
        BIGINT admin_id UK "UNIQUE NOT NULL"
        BOOLEAN notifications_enabled "DEFAULT TRUE"
        TIMESTAMP updated_at "DEFAULT CURRENT_TIMESTAMP"
    }
    
    user_blocks {
        SERIAL id PK
        BIGINT user_id FK "REFERENCES users(telegram_id)" "UNIQUE"
        BIGINT blocked_by "NOT NULL"
        TEXT reason
        TIMESTAMP blocked_at "DEFAULT CURRENT_TIMESTAMP"
    }
    
    broadcasts {
        SERIAL id PK
        BIGINT admin_id "NOT NULL"
        TEXT message_text
        VARCHAR message_type "DEFAULT 'text'"
        VARCHAR file_id
        BOOLEAN send_to_active_only "DEFAULT FALSE"
        VARCHAR status "DEFAULT 'pending'"
        TIMESTAMP scheduled_at
        TIMESTAMP sent_at
        INTEGER total_users "DEFAULT 0"
        INTEGER success_count "DEFAULT 0"
        INTEGER failed_count "DEFAULT 0"
        TIMESTAMP created_at "DEFAULT CURRENT_TIMESTAMP"
    }
    
    tuition_prices {
        SERIAL id PK
        VARCHAR specialty_name "NOT NULL"
        VARCHAR specialty_code
        VARCHAR education_level "NOT NULL"
        VARCHAR study_form "NOT NULL"
        VARCHAR price_monthly
        VARCHAR price_semester
        VARCHAR price_year
        VARCHAR price_total
        VARCHAR academic_year
        TIMESTAMP created_at "DEFAULT CURRENT_TIMESTAMP"
        TIMESTAMP updated_at "DEFAULT CURRENT_TIMESTAMP"
        UNIQUE "specialty_name, specialty_code, education_level, study_form"
    }
```

## Опис таблиць

### users
Основна таблиця користувачів бота. Зберігає інформацію про Telegram-користувачів.

### reminders
Нагадування про важливі дати (дедлайни подачі документів тощо).

### documents
Список документів, необхідних для вступу.

### message_history
Історія всіх повідомлень користувачів та відповідей бота.

### response_feedback
Відгуки користувачів на відповіді бота (👍/👎).

### shared_contacts
Контакти, якими поділилися користувачі для зв'язку з приймальною комісією.

### admin_settings
Налаштування адміністраторів бота.

### user_blocks
Заблоковані користувачі.

### broadcasts
Розсилки повідомлень від адміністраторів до користувачів.

### tuition_prices
Вартості навчання для різних спеціальностей, рівнів освіти та форм навчання.





