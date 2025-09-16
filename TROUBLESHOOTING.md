# 🔧 Устранение неполадок - Telegram Bot для поиска квартир

## 🚨 Частые проблемы и их решения

### 1. Бот не запускается

#### Ошибка: "BOT_TOKEN не настроен"
```bash
# Решение: Проверьте файл .env
cat .env
# Должно быть:
BOT_TOKEN=your_actual_token_here

# Если файла нет:
cp env_example.txt .env
# Отредактируйте .env и добавьте токен
```

#### Ошибка: "ModuleNotFoundError"
```bash
# Решение: Установите зависимости
pip install -r requirements.txt

# Или создайте виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

#### Ошибка: "Permission denied"
```bash
# Решение: Проверьте права доступа
ls -la
chmod +w .  # Linux/Mac
# Windows: Запустите от имени администратора
```

### 2. База данных не работает

#### Ошибка: "Database locked"
```bash
# Решение: Удалите заблокированную базу
rm apartments.db
# Перезапустите бота - база создастся автоматически
```

#### Ошибка: "Table doesn't exist"
```bash
# Решение: Проверьте создание таблиц
python -c "
from database import create_tables
create_tables()
print('Tables created successfully')
"
```

#### Ошибка: "SQLite version too old"
```bash
# Решение: Обновите Python или используйте PostgreSQL
# В .env:
DATABASE_URL=postgresql://user:pass@localhost/dbname
```

### 3. AI функции не работают

#### Ошибка: "OpenAI API key not found"
```bash
# Решение: Добавьте API ключ в .env
echo "OPENAI_API_KEY=your_key_here" >> .env

# Или отключите AI функции:
echo "ENABLE_AI_ANALYSIS=false" >> .env
```

#### Ошибка: "Transformers not installed"
```bash
# Решение: Установите AI зависимости
pip install transformers torch openai

# Или используйте только базовые функции:
echo "ENABLE_AI_ANALYSIS=false" >> .env
```

#### Ошибка: "CUDA not available"
```bash
# Решение: Установите CPU версию PyTorch
pip uninstall torch
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### 4. Мониторинг не работает

#### Ошибка: "No apartments found"
```bash
# Решение: Проверьте логи
tail -f bot.log

# Проверьте статус мониторинга
# В боте: /admin -> /status

# Принудительно запустите проверку
# В боте: /admin -> /force_check
```

#### Ошибка: "Scraper failed"
```bash
# Решение: Проверьте интернет соединение
ping google.com

# Проверьте API ключи (если есть)
cat .env | grep API_KEY

# Проверьте доступность сайтов
curl -I https://www.immobilienscout24.de
```

#### Ошибка: "Rate limit exceeded"
```bash
# Решение: Увеличьте интервал проверки
# В config.py:
CHECK_INTERVAL = 300  # 5 минут вместо 1 минуты

# Или добавьте задержки в скраперы
```

### 5. Уведомления не отправляются

#### Ошибка: "Bot instance not set"
```bash
# Решение: Проверьте инициализацию бота
# В bot.py должно быть:
set_bot_instance(bot)

# Перезапустите бота
```

#### Ошибка: "User not found"
```bash
# Решение: Проверьте базу данных
python -c "
from database import DatabaseManager
db = DatabaseManager()
users = db.get_users_with_active_subscriptions()
print(f'Active users: {len(users)}')
"
```

#### Ошибка: "Message too long"
```bash
# Решение: Укоротите текст уведомлений
# В notifications.py ограничьте длину описания
apartment.description[:150] + "..."
```

### 6. Производительность

#### Бот работает медленно
```bash
# Решение: Оптимизируйте настройки
# В config.py:
CHECK_INTERVAL = 300      # Проверка каждые 5 минут
MAX_RETRIES = 1          # Уменьшите количество повторов

# Используйте Redis для кэширования
echo "REDIS_URL=redis://localhost:6379" >> .env
```

#### Высокое потребление памяти
```bash
# Решение: Ограничьте количество одновременных запросов
# В scrapers.py добавьте семафоры
import asyncio
semaphore = asyncio.Semaphore(5)  # Максимум 5 одновременных запросов
```

#### База данных растет слишком быстро
```bash
# Решение: Добавьте очистку старых данных
# В database.py добавьте функцию очистки
def cleanup_old_data(days=30):
    # Удаление старых квартир и уведомлений
    pass
```

## 🔍 Диагностика

### Проверка логов
```bash
# Последние ошибки
grep "ERROR" bot.log | tail -10

# Проверка мониторинга
grep "monitoring" bot.log | tail -5

# Проверка уведомлений
grep "notification" bot.log | tail -5
```

### Проверка базы данных
```bash
# Размер базы
ls -lh apartments.db

# Количество записей
python -c "
from database import DatabaseManager
from models import User, Apartment, Subscription
db = DatabaseManager()
session = db.SessionLocal()
print(f'Users: {session.query(User).count()}')
print(f'Apartments: {session.query(Apartment).count()}')
print(f'Subscriptions: {session.query(Subscription).count()}')
session.close()
"
```

### Проверка сети
```bash
# Доступность сайтов недвижимости
curl -I https://www.immobilienscout24.de
curl -I https://www.immowelt.de

# Проверка API ключей
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print(f'BOT_TOKEN: {bool(os.getenv(\"BOT_TOKEN\"))}')
print(f'OPENAI_API_KEY: {bool(os.getenv(\"OPENAI_API_KEY\"))}')
"
```

## 🛠️ Восстановление после сбоя

### Полная перезагрузка
```bash
# 1. Остановите бота
pkill -f "python.*bot.py"

# 2. Очистите временные файлы
rm -f *.pyc __pycache__/*

# 3. Перезапустите
python run.py
```

### Сброс базы данных
```bash
# ВНИМАНИЕ: Все данные будут потеряны!
rm apartments.db
python run.py  # База создастся заново
```

### Восстановление из резервной копии
```bash
# Если у вас есть резервная копия
cp apartments.db.backup apartments.db
python run.py
```

## 📞 Получение помощи

### 1. Проверьте логи
```bash
tail -f bot.log
```

### 2. Запустите в режиме отладки
```bash
# В config.py измените уровень логирования
logging.basicConfig(level=logging.DEBUG)
```

### 3. Проверьте системные требования
```bash
python --version  # Должен быть 3.8+
pip list | grep -E "(aiogram|sqlalchemy|aiohttp)"
```

### 4. Создайте минимальный тест
```python
# test_minimal.py
import asyncio
from aiogram import Bot

async def test_bot():
    bot = Bot("YOUR_TOKEN")
    try:
        me = await bot.get_me()
        print(f"Bot connected: {me.first_name}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await bot.session.close()

asyncio.run(test_bot())
```

## 🎯 Профилактика проблем

### Ежедневные проверки
- [ ] Мониторинг логов на ошибки
- [ ] Проверка размера базы данных
- [ ] Тест отправки уведомлений
- [ ] Проверка доступности сайтов

### Еженедельные проверки
- [ ] Очистка старых данных
- [ ] Проверка обновлений зависимостей
- [ ] Тест AI функций
- [ ] Резервное копирование базы

### Ежемесячные проверки
- [ ] Анализ производительности
- [ ] Проверка безопасности
- [ ] Обновление документации
- [ ] Оптимизация настроек

---

**Большинство проблем решается перезапуском и проверкой конфигурации** 🔧✅
