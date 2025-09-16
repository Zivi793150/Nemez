# Настройка MongoDB для бота

## Варианты установки MongoDB

### 1. MongoDB Atlas (Облачная база данных) - Рекомендуется

1. **Зарегистрируйтесь на MongoDB Atlas:**
   - Перейдите на https://www.mongodb.com/atlas
   - Создайте бесплатный аккаунт

2. **Создайте кластер:**
   - Выберите "Free" план
   - Выберите провайдера (AWS, Google Cloud, Azure)
   - Выберите регион (желательно близко к вам)
   - Нажмите "Create"

3. **Настройте доступ:**
   - В разделе "Security" → "Database Access"
   - Создайте пользователя с паролем
   - В разделе "Security" → "Network Access"
   - Добавьте IP адрес `0.0.0.0/0` (для доступа откуда угодно)

4. **Получите строку подключения:**
   - В разделе "Deployment" → "Database"
   - Нажмите "Connect"
   - Выберите "Connect your application"
   - Скопируйте строку подключения

5. **Обновите .env файл:**
   ```
   MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/
   MONGODB_DATABASE=nemez2_bot
   ```

### 2. Локальная установка MongoDB

#### Windows:
1. Скачайте MongoDB Community Server с https://www.mongodb.com/try/download/community
2. Установите с настройками по умолчанию
3. MongoDB будет доступен на `mongodb://localhost:27017`

#### macOS:
```bash
# Установка через Homebrew
brew tap mongodb/brew
brew install mongodb-community

# Запуск MongoDB
brew services start mongodb/brew/mongodb-community
```

#### Linux (Ubuntu/Debian):
```bash
# Импорт публичного ключа
wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | sudo apt-key add -

# Добавление репозитория
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list

# Обновление и установка
sudo apt-get update
sudo apt-get install -y mongodb-org

# Запуск MongoDB
sudo systemctl start mongod
sudo systemctl enable mongod
```

## Настройка .env файла

Создайте файл `.env` в корневой папке проекта:

```env
# Bot Configuration
BOT_TOKEN=your_bot_token_here

# MongoDB Configuration
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=nemez2_bot

# AI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-3.5-turbo
ENABLE_AI_ANALYSIS=true

# Monitoring Configuration
SCRAPING_DELAY=30
MAX_APARTMENTS_PER_SEARCH=10

# Logging
LOG_LEVEL=INFO
```

## Проверка подключения

После настройки запустите бота:

```bash
python run.py
```

Если всё настроено правильно, вы увидите:
```
✅ Конфигурация проверена
✅ Все зависимости установлены
📁 Директории созданы
🚀 Запуск бота...
Connected to MongoDB: mongodb://localhost:27017
Database indexes created successfully
```

## Структура базы данных

Бот автоматически создаст следующие коллекции:

- **users** - пользователи бота
- **subscriptions** - подписки пользователей
- **user_filters** - фильтры поиска пользователей
- **apartments** - найденные квартиры
- **notifications** - уведомления о новых квартирах

## Полезные команды MongoDB

### Подключение к MongoDB:
```bash
mongosh
```

### Просмотр баз данных:
```javascript
show dbs
```

### Использование базы данных:
```javascript
use nemez2_bot
```

### Просмотр коллекций:
```javascript
show collections
```

### Просмотр документов:
```javascript
db.users.find()
db.apartments.find()
```

### Подсчет документов:
```javascript
db.users.countDocuments()
db.apartments.countDocuments()
```
