# 🏠 German Apartment Finder

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Современное веб-приложение для поиска квартир в Германии с продвинутыми возможностями мониторинга, уведомлений и AI-анализа.

## ✨ Основные возможности

### 🔍 **Поиск и мониторинг**
- **Мгновенные уведомления** - получайте уведомления в течение секунд после появления новых квартир
- **Мониторинг всех основных сайтов** - ImmoScout24, Immowelt и других
- **Продвинутые фильтры** - по району, цене, количеству комнат, площади, этажу
- **Поиск по ключевым словам** - найдите квартиры с нужными характеристиками

### 🤖 **Искусственный интеллект**
- **AI-анализ квартир** - автоматический анализ плюсов и минусов каждой квартиры
- **Умные рекомендации** - персонализированные предложения на основе ваших предпочтений
- **Анализ рынка** - статистика цен и трендов в разных районах

### 💳 **Подписка и платежи**
- **Месячная подписка** - доступ к полному функционалу
- **Безопасные платежи** - интеграция со Stripe
- **Гибкие планы** - разные тарифы для разных потребностей

### 🌍 **Мультиязычность**
- **Поддержка языков** - немецкий, русский, украинский
- **Локализованный интерфейс** - адаптация под каждый язык
- **Локализованные уведомления** - получайте уведомления на родном языке

## 🏗️ Архитектура

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend       │    │   Backend API    │    │   Background    │
│   (HTML/CSS/JS)  │◄──►│   (FastAPI)      │◄──►│   Services      │
│                 │    │                 │    │                 │
│ • User Dashboard│    │ • REST API      │    │ • Web Scrapers  │
│ • Search UI     │    │ • Authentication │    │ • Monitoring    │
│ • Notifications │    │ • Database       │    │ • AI Analysis   │
│ • Payment Forms │    │ • Email Service  │    │ • Notifications │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🛠️ Технологический стек

### **Backend**
- **FastAPI** - современный веб-фреймворк для Python
- **SQLAlchemy** - ORM для работы с базой данных
- **PostgreSQL/SQLite** - база данных
- **Redis** - кэширование и очереди задач
- **Celery** - фоновые задачи

### **Frontend**
- **HTML5/CSS3** - семантическая разметка
- **Tailwind CSS** - утилитарный CSS-фреймворк
- **JavaScript (Vanilla)** - интерактивность
- **Jinja2** - серверный рендеринг шаблонов

### **Дополнительные технологии**
- **OpenAI API** - искусственный интеллект
- **Stripe** - обработка платежей
- **BeautifulSoup4/Selenium** - веб-скрапинг
- **JWT** - аутентификация
- **SMTP** - отправка email

## 🚀 Быстрый старт

### **1. Клонирование репозитория**

```bash
git clone https://github.com/Zivi793150/Nemez.git
cd Nemez
```

### **2. Установка зависимостей**

```bash
# Создайте виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows

# Установите зависимости
pip install -r requirements.txt
```

### **3. Настройка окружения**

```bash
# Скопируйте файл с переменными окружения
cp env_web_example.txt .env

# Отредактируйте .env файл
# Укажите необходимые API ключи и настройки
```

### **4. Минимальная конфигурация**

Для начала работы вам нужны только эти переменные:

```bash
# Обязательные
DATABASE_URL=sqlite:///./apartment_web.db
JWT_SECRET_KEY=your_super_secret_jwt_key_here_make_it_long_and_random
SECRET_KEY=your_super_secret_key_for_password_hashing

# Настройки сервера
WEB_HOST=0.0.0.0
WEB_PORT=8000
DEBUG=true
```

### **5. Запуск приложения**

```bash
# Простой запуск
python run.py

# Или с помощью uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### **6. Откройте браузер**

Перейдите по адресу: **http://localhost:8000**

## 🐳 Docker (рекомендуется)

### **Быстрый запуск с Docker**

```bash
# Запуск всех сервисов
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down
```

### **Полезные команды**

```bash
# Сборка образа
make docker-build

# Запуск сервисов
make docker-run

# Остановка сервисов
make docker-stop

# Просмотр логов
make docker-logs
```

## 📁 Структура проекта

```
Nemez/
├── main.py                 # Точка входа приложения
├── run.py                  # Скрипт запуска
├── requirements.txt        # Зависимости Python
├── env_web_example.txt     # Пример переменных окружения
├── Dockerfile              # Docker образ
├── docker-compose.yml      # Docker Compose конфигурация
├── Makefile                # Полезные команды
├── README.md              # Документация
├── DEPLOYMENT.md          # Руководство по развертыванию
├── QUICK_START.md         # Быстрый старт
├── .github/               # GitHub Actions
├── app/                   # Основной код приложения
│   ├── __init__.py
│   ├── api/               # API endpoints
│   ├── core/              # Основные компоненты
│   ├── config/            # Конфигурация
│   ├── database/          # База данных
│   ├── models/            # Модели данных
│   ├── services/          # Бизнес-логика
│   └── scrapers/          # Веб-скраперы
├── templates/             # HTML шаблоны
│   ├── base.html          # Базовый шаблон
│   └── index.html         # Главная страница
└── static/                # Статические файлы
```

## 🔧 Конфигурация

### **Основные настройки**

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `DATABASE_URL` | URL базы данных | `sqlite:///./apartment_web.db` |
| `WEB_HOST` | Хост веб-сервера | `0.0.0.0` |
| `WEB_PORT` | Порт веб-сервера | `8000` |
| `DEBUG` | Режим отладки | `true` |
| `JWT_SECRET_KEY` | Секретный ключ JWT | Обязательно |
| `SECRET_KEY` | Секретный ключ | Обязательно |

### **API ключи**

| Сервис | Переменная | Описание |
|--------|------------|----------|
| OpenAI | `OPENAI_API_KEY` | Для AI-анализа квартир |
| Stripe | `STRIPE_SECRET_KEY` | Для обработки платежей |
| Google Maps | `GOOGLE_MAPS_API_KEY` | Для геокодирования |

## 📊 API Endpoints

### **Аутентификация**
- `POST /api/v1/auth/register` - Регистрация пользователя
- `POST /api/v1/auth/login` - Вход в систему
- `GET /api/v1/auth/me` - Информация о текущем пользователе

### **Пользователи**
- `GET /api/v1/users/profile` - Профиль пользователя
- `PUT /api/v1/users/profile` - Обновление профиля

### **Квартиры**
- `GET /api/v1/apartments` - Список квартир
- `GET /api/v1/apartments/{id}` - Детали квартиры
- `POST /api/v1/apartments/search` - Поиск квартир

### **Фильтры**
- `GET /api/v1/filters` - Список фильтров пользователя
- `POST /api/v1/filters` - Создание фильтра
- `PUT /api/v1/filters/{id}` - Обновление фильтра

## 🔍 Документация API

После запуска приложения откройте:
**http://localhost:8000/docs**

Здесь вы найдете интерактивную документацию API с возможностью тестирования endpoints.

## 🧪 Тестирование

```bash
# Запуск всех тестов
make test

# Запуск тестов с покрытием
pytest --cov=app --cov-report=html

# Запуск конкретных тестов
pytest tests/test_api.py
```

## 🚀 Развертывание

### **Автоматическое развертывание**

Приложение настроено для автоматического развертывания через GitHub Actions.

**Настройка секретов:**
1. Перейдите в Settings → Secrets and variables → Actions
2. Добавьте необходимые секреты (см. DEPLOYMENT.md)

**Автоматическое развертывание:**
```bash
git push origin main
```

### **Ручное развертывание**

Подробные инструкции по развертыванию в различных средах см. в [DEPLOYMENT.md](DEPLOYMENT.md).

## 🔒 Безопасность

- JWT токены для аутентификации
- Хеширование паролей с bcrypt
- Валидация входных данных с Pydantic
- Защита от SQL injection и XSS атак
- CORS настройки
- Rate limiting для API endpoints

## 📈 Производительность

- Кэширование с Redis
- Асинхронные запросы с FastAPI
- Фоновые задачи с Celery
- Пул соединений с базой данных
- Мониторинг и логирование

## 🤝 Вклад в проект

1. Fork репозитория
2. Создайте feature branch (`git checkout -b feature/amazing-feature`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push в branch (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## 📞 Поддержка

- **Email**: support@apartmentfinder.com
- **Документация**: `/docs` (Swagger UI)
- **Issues**: [GitHub Issues](https://github.com/Zivi793150/Nemez/issues)

## 📄 Лицензия

Этот проект лицензирован под MIT License - см. файл [LICENSE](LICENSE) для деталей.

## 🙏 Благодарности

- [FastAPI](https://fastapi.tiangolo.com/) - за отличный веб-фреймворк
- [Tailwind CSS](https://tailwindcss.com/) - за утилитарный CSS
- [OpenAI](https://openai.com/) - за AI API
- [Stripe](https://stripe.com/) - за платежную систему

---

**German Apartment Finder** - Найдите свой идеальный дом в Германии! 🏠✨

**⭐ Не забудьте поставить звездочку репозиторию!**
