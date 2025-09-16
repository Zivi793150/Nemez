# 🚀 Быстрый старт

## Установка за 5 минут

### 1. Клонирование и настройка
```bash
git clone <repository-url>
cd apartment-search-bot
python setup.py
```

### 2. Настройка API ключей
Отредактируйте файл `.env` и добавьте ваши API ключи:

```env
# Обязательно
BOT_TOKEN=your_telegram_bot_token_here

# Для реальных данных (рекомендуется)
ESTATESYNC_API_KEY=your_estatesync_api_key_here
IMMOSCOUT24_API_KEY=your_immoscout24_api_key_here

# Опционально
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Запуск MongoDB
```bash
# С Docker
docker run -d -p 27017:27017 --name mongodb mongo:latest

# Или установите MongoDB локально
```

### 4. Тестирование
```bash
python test_env.py
```

### 5. Запуск бота
```bash
python run.py
```

## Получение API ключей

### EstateSync API (основной источник)
1. Зарегистрируйтесь на [estatesync.io](https://estatesync.io)
2. Создайте проект
3. Получите API ключ
4. Добавьте в `ESTATESYNC_API_KEY`

### ImmoScout24 API
1. Зарегистрируйтесь как партнер на [ImmoScout24](https://www.immobilienscout24.de/partner)
2. Подайте заявку на API
3. Получите ключ
4. Добавьте в `IMMOSCOUT24_API_KEY`

## Использование бота

1. **Запустите бота**: `/start`
2. **Выберите язык**: немецкий/русский/украинский
3. **Оформите подписку**: нажмите "Оплатить подписку"
4. **Настройте фильтры**: город, цена, комнаты
5. **Получайте уведомления**: о новых квартирах

## Команды бота

- `/start` - запуск бота
- `/language` - смена языка
- `/filters` - настройка фильтров
- `/settings` - настройки
- `/stats` - статистика
- `/help` - помощь

## Troubleshooting

### "API key not configured"
- Проверьте файл `.env`
- Убедитесь, что API ключи добавлены

### "MongoDB connection failed"
- Запустите MongoDB: `docker run -d -p 27017:27017 mongo:latest`

### "No apartments found"
- Проверьте настройки фильтров
- Убедитесь, что API ключи активны

## Поддержка

- 📚 [API_SETUP.md](API_SETUP.md) - подробная настройка API
- 📖 [README.md](README.md) - полная документация
- 🔧 [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - решение проблем
