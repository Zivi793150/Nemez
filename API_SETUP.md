# Настройка API ключей для получения реальных данных

## Обзор

Этот бот использует несколько источников данных для поиска квартир в Германии:

1. **EstateSync API** - основной источник реальных данных
2. **ImmoScout24 API** - официальный API ImmoScout24
3. **Web Scraping** - резервный метод для получения данных

## Настройка переменных окружения

Создайте файл `.env` в корневой директории проекта со следующими переменными:

```env
# Telegram Bot Configuration
BOT_TOKEN=your_telegram_bot_token_here

# Database Configuration
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=nemez2_bot

# Redis Configuration (optional)
REDIS_URL=redis://localhost:6379

# API Keys for Real Estate Sites
IMMOSCOUT24_API_KEY=your_immoscout24_api_key_here
IMMOWELT_API_KEY=your_immowelt_api_key_here
ESTATESYNC_API_KEY=your_estatesync_api_key_here

# AI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-3.5-turbo
ENABLE_AI_ANALYSIS=true

# Subscription Settings
SUBSCRIPTION_PRICE=9.99
SUBSCRIPTION_DURATION=30

# Monitoring Settings
CHECK_INTERVAL=60
MAX_RETRIES=3
MAX_PRICE_CAP=5000
```

## Получение API ключей

### 1. EstateSync API

EstateSync - это сервис, который предоставляет доступ к данным о недвижимости из различных источников.

**Как получить ключ:**
1. Зарегистрируйтесь на [estatesync.io](https://estatesync.io)
2. Создайте новый проект
3. Получите API ключ в разделе "API Keys"
4. Добавьте ключ в переменную `ESTATESYNC_API_KEY`

### 2. ImmoScout24 API

ImmoScout24 предоставляет официальный API для доступа к данным о недвижимости.

**Как получить ключ:**
1. Зарегистрируйтесь как партнер на [ImmoScout24](https://www.immobilienscout24.de/partner)
2. Подайте заявку на доступ к API
3. После одобрения получите API ключ
4. Добавьте ключ в переменную `IMMOSCOUT24_API_KEY`

### 3. Immowelt API

Immowelt также предоставляет API для доступа к данным.

**Как получить ключ:**
1. Свяжитесь с Immowelt для получения доступа к API
2. Получите API ключ
3. Добавьте ключ в переменную `IMMOWELT_API_KEY`

## Приоритет источников данных

Бот использует следующие источники в порядке приоритета:

1. **EstateSync API** - самый надежный источник
2. **ImmoScout24 API** - официальный API
3. **Web Scraping** - резервный метод

Если API ключи не настроены, бот будет использовать только веб-скрапинг.

## Тестирование API

После настройки API ключей вы можете протестировать их работу:

```bash
# Запустите тест
python test_env.py
```

## Мониторинг

Бот автоматически мониторит новые объявления каждую минуту и уведомляет пользователей о новых квартирах, соответствующих их фильтрам.

## Troubleshooting

### Проблема: "API key not configured"
**Решение:** Проверьте, что API ключи правильно добавлены в файл `.env`

### Проблема: "Unauthorized (401)"
**Решение:** Проверьте правильность API ключа и его активность

### Проблема: "No apartments found"
**Решение:** 
1. Проверьте настройки фильтров
2. Убедитесь, что API ключи активны
3. Попробуйте расширить диапазон поиска

## Безопасность

- Никогда не коммитьте файл `.env` в репозиторий
- Храните API ключи в безопасном месте
- Регулярно обновляйте API ключи
- Используйте ограничения по IP, если API это поддерживает
