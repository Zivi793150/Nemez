# 🚀 Руководство по развертыванию

## 📋 Обзор

Это руководство поможет вам развернуть **German Apartment Finder** веб-приложение в различных средах.

## 🐳 Развертывание с Docker (рекомендуется)

### **Быстрый старт**

```bash
# 1. Клонируйте репозиторий
git clone https://github.com/Zivi793150/Nemez.git
cd Nemez

# 2. Скопируйте переменные окружения
cp env_web_example.txt .env

# 3. Отредактируйте .env файл
# Укажите необходимые API ключи и настройки

# 4. Запустите с Docker Compose
docker-compose up -d

# 5. Откройте браузер
# http://localhost:8000
```

### **Команды Docker**

```bash
# Сборка образа
make docker-build

# Запуск всех сервисов
make docker-run

# Остановка сервисов
make docker-stop

# Просмотр логов
make docker-logs

# Открыть shell в контейнере
make docker-shell
```

## ☁️ Развертывание в облаке

### **Heroku**

```bash
# 1. Установите Heroku CLI
# https://devcenter.heroku.com/articles/heroku-cli

# 2. Создайте приложение
heroku create your-app-name

# 3. Добавьте PostgreSQL
heroku addons:create heroku-postgresql:mini

# 4. Добавьте Redis
heroku addons:create heroku-redis:mini

# 5. Настройте переменные окружения
heroku config:set JWT_SECRET_KEY=your_secret_key
heroku config:set SECRET_KEY=your_secret_key
heroku config:set OPENAI_API_KEY=your_openai_key

# 6. Разверните
git push heroku main
```

### **DigitalOcean App Platform**

1. Создайте новый App в DigitalOcean
2. Подключите GitHub репозиторий
3. Выберите ветку `main`
4. Настройте переменные окружения
5. Разверните

### **AWS Elastic Beanstalk**

```bash
# 1. Установите EB CLI
pip install awsebcli

# 2. Инициализируйте приложение
eb init

# 3. Создайте окружение
eb create production

# 4. Разверните
eb deploy
```

## 🐧 Развертывание на VPS

### **Подготовка сервера**

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Создание пользователя для приложения
sudo adduser appuser
sudo usermod -aG docker appuser
```

### **Развертывание приложения**

```bash
# 1. Подключитесь к серверу
ssh user@your-server-ip

# 2. Клонируйте репозиторий
git clone https://github.com/Zivi793150/Nemez.git
cd Nemez

# 3. Скопируйте переменные окружения
cp env_web_example.txt .env

# 4. Отредактируйте .env файл
nano .env

# 5. Запустите приложение
docker-compose up -d

# 6. Проверьте статус
docker-compose ps
```

### **Настройка Nginx (опционально)**

```bash
# Установка Nginx
sudo apt install nginx

# Создание конфигурации
sudo nano /etc/nginx/sites-available/apartment-finder

# Содержимое конфигурации:
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Активация сайта
sudo ln -s /etc/nginx/sites-available/apartment-finder /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### **Настройка SSL с Let's Encrypt**

```bash
# Установка Certbot
sudo apt install certbot python3-certbot-nginx

# Получение SSL сертификата
sudo certbot --nginx -d your-domain.com

# Автоматическое обновление
sudo crontab -e
# Добавьте строку:
# 0 12 * * * /usr/bin/certbot renew --quiet
```

## 🔄 Непрерывное развертывание

### **GitHub Actions**

Приложение уже настроено для автоматического развертывания через GitHub Actions.

**Настройка секретов:**

1. Перейдите в Settings → Secrets and variables → Actions
2. Добавьте следующие секреты:
   - `DOCKER_USERNAME` - ваш Docker Hub логин
   - `DOCKER_PASSWORD` - ваш Docker Hub пароль
   - `HOST` - IP адрес вашего сервера
   - `USERNAME` - имя пользователя на сервере
   - `KEY` - приватный SSH ключ

**Автоматическое развертывание:**

```bash
# При каждом push в main ветку
git push origin main

# GitHub Actions автоматически:
# 1. Запустит тесты
# 2. Соберет Docker образ
# 3. Развернет на сервере
```

## 📊 Мониторинг и логи

### **Просмотр логов**

```bash
# Логи веб-приложения
docker-compose logs -f web

# Логи базы данных
docker-compose logs -f db

# Логи Redis
docker-compose logs -f redis

# Логи Celery
docker-compose logs -f celery
```

### **Мониторинг ресурсов**

```bash
# Использование ресурсов контейнеров
docker stats

# Проверка здоровья приложения
curl http://localhost:8000/health

# Статус сервисов
docker-compose ps
```

## 🔒 Безопасность

### **Обязательные настройки**

```bash
# В .env файле:
JWT_SECRET_KEY=very_long_random_string_here
SECRET_KEY=another_very_long_random_string_here
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
```

### **Firewall настройки**

```bash
# Открыть только необходимые порты
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw enable
```

### **Регулярные обновления**

```bash
# Обновление Docker образов
docker-compose pull
docker-compose up -d

# Обновление системы
sudo apt update && sudo apt upgrade -y
```

## 🚨 Устранение неполадок

### **Частые проблемы**

**Приложение не запускается:**
```bash
# Проверьте логи
docker-compose logs web

# Проверьте переменные окружения
docker-compose exec web env | grep -E "(DATABASE|REDIS|JWT)"
```

**База данных не подключается:**
```bash
# Проверьте статус PostgreSQL
docker-compose ps db

# Проверьте логи базы данных
docker-compose logs db
```

**Redis не работает:**
```bash
# Перезапустите Redis
docker-compose restart redis

# Проверьте подключение
docker-compose exec web redis-cli -h redis ping
```

### **Восстановление из резервной копии**

```bash
# Остановка приложения
docker-compose down

# Восстановление базы данных
docker-compose exec db pg_restore -U postgres -d apartment_finder backup.sql

# Запуск приложения
docker-compose up -d
```

## 📈 Масштабирование

### **Горизонтальное масштабирование**

```bash
# Увеличение количества веб-серверов
docker-compose up -d --scale web=3

# Балансировка нагрузки с Nginx
# Настройте upstream в конфигурации Nginx
```

### **Вертикальное масштабирование**

```bash
# В docker-compose.yml добавьте ограничения ресурсов:
services:
  web:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
```

## 📞 Поддержка

Если у вас возникли проблемы с развертыванием:

1. Проверьте логи: `docker-compose logs`
2. Убедитесь, что все переменные окружения настроены
3. Проверьте статус сервисов: `docker-compose ps`
4. Обратитесь к документации в `README.md`

---

**Удачи с развертыванием! 🚀**
