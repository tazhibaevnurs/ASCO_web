# 🚀 Руководство по развертыванию ASCO.KG на сервере

## 📋 Предварительные требования

- Сервер с Ubuntu/Debian
- Доступ root: `root@31.207.74.12`
- Домен: `asco.kg` и `www.asco.kg`
- Git репозиторий: `https://github.com/tazhibaevnurs/ASCO_web`

## 📝 Пошаговая инструкция

### Шаг 1: Подключение к серверу

```bash
ssh root@31.207.74.12
```

### Шаг 2: Установка необходимого ПО

```bash
# Обновление системы
apt update && apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Установка Docker Compose
apt install docker-compose -y

# Установка Git
apt install git -y

# Установка Certbot для SSL
apt install certbot -y
```

### Шаг 3: Клонирование репозитория

```bash
# Создаем директорию для проекта
mkdir -p /var/www
cd /var/www

# Клонируем репозиторий
git clone https://github.com/tazhibaevnurs/ASCO_web.git
cd ASCO_web
```

### Шаг 4: Настройка переменных окружения

```bash
# Создаем .env файл
nano .env
```

Вставьте следующее содержимое (обязательно измените пароли!):

```env
# Django Settings
SECRET_KEY=ваш-секретный-ключ-здесь
DEBUG=False
ALLOWED_HOSTS=asco.kg,www.asco.kg
TIME_ZONE=Asia/Bishkek
CSRF_TRUSTED_ORIGINS=https://asco.kg,https://www.asco.kg

# Database Configuration
DB_NAME=ascodb
DB_USER=ascouser
DB_PASSWORD=надежный-пароль-для-базы-данных
DB_HOST=db
DB_PORT=5432

# PostgreSQL (для docker-compose)
POSTGRES_DB=ascodb
POSTGRES_USER=ascouser
POSTGRES_PASSWORD=надежный-пароль-для-базы-данных
```

**Важно:** 
- Сгенерируйте SECRET_KEY: `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`
- Используйте надежные пароли для базы данных

### Шаг 5: Настройка DNS

Убедитесь, что DNS записи настроены правильно:

```
A     asco.kg          → 31.207.74.12
A     www.asco.kg       → 31.207.74.12
```

Проверьте DNS:
```bash
dig asco.kg +short
dig www.asco.kg +short
```

### Шаг 6: Первый запуск (без SSL)

```bash
# Делаем скрипт развертывания исполняемым
chmod +x deploy.sh

# Запускаем развертывание
./deploy.sh
```

Или вручную:

```bash
# Создаем необходимые директории
mkdir -p logs nginx/ssl certbot/conf certbot/www

# Запускаем контейнеры
docker-compose up -d --build

# Ждем готовности базы данных
sleep 10

# Применяем миграции
docker-compose exec web python manage.py migrate --noinput

# Собираем статические файлы
docker-compose exec web python manage.py collectstatic --noinput
```

### Шаг 7: Получение SSL сертификата (Let's Encrypt)

```bash
# Останавливаем nginx временно
docker-compose stop nginx

# Получаем сертификат
certbot certonly --standalone \
  --email your-email@example.com \
  --agree-tos \
  --no-eff-email \
  -d asco.kg \
  -d www.asco.kg

# Копируем сертификаты в нужную директорию
mkdir -p nginx/ssl
cp /etc/letsencrypt/live/asco.kg/fullchain.pem nginx/ssl/
cp /etc/letsencrypt/live/asco.kg/privkey.pem nginx/ssl/
```

### Шаг 8: Обновление Nginx конфигурации для HTTPS

Обновите `nginx.conf` для поддержки HTTPS:

```nginx
server {
    listen 80;
    server_name asco.kg www.asco.kg;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name asco.kg www.asco.kg;

    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    client_max_body_size 100M;

    # Certbot verification
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Serve static files
    location /static/ {
        alias /app/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Serve media files
    location /media/ {
        alias /app/media/;
        expires 7d;
        add_header Cache-Control "public";
    }

    # Proxy all other requests to Django
    location / {
        proxy_pass http://web:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
}
```

### Шаг 9: Перезапуск с SSL

```bash
# Перезапускаем nginx
docker-compose up -d nginx
```

### Шаг 10: Создание суперпользователя

```bash
docker-compose exec web python manage.py createsuperuser
```

## 🔧 Полезные команды

### Просмотр логов
```bash
# Все сервисы
docker-compose logs -f

# Только Django
docker-compose logs -f web

# Только Nginx
docker-compose logs -f nginx

# Только PostgreSQL
docker-compose logs -f db
```

### Остановка/Запуск
```bash
# Остановить все
docker-compose down

# Запустить все
docker-compose up -d

# Перезапустить конкретный сервис
docker-compose restart web
```

### Обновление кода
```bash
cd /var/www/ASCO_web
git pull origin master
docker-compose up -d --build
docker-compose exec web python manage.py migrate --noinput
docker-compose exec web python manage.py collectstatic --noinput
```

### Доступ к контейнерам
```bash
# Django shell
docker-compose exec web python manage.py shell

# Bash в контейнере
docker-compose exec web bash

# PostgreSQL
docker-compose exec db psql -U ascouser -d ascodb
```

### Обновление SSL сертификата
```bash
# Автоматическое обновление (добавьте в crontab)
certbot renew --dry-run

# Обновление сертификатов
certbot renew
cp /etc/letsencrypt/live/asco.kg/fullchain.pem nginx/ssl/
cp /etc/letsencrypt/live/asco.kg/privkey.pem nginx/ssl/
docker-compose restart nginx
```

## 🔒 Безопасность

1. **Firewall**: Настройте UFW
```bash
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

2. **Регулярные обновления**
```bash
apt update && apt upgrade -y
docker-compose pull
docker-compose up -d --build
```

3. **Резервное копирование базы данных**
```bash
# Создать бэкап
docker-compose exec db pg_dump -U ascouser ascodb > backup_$(date +%Y%m%d).sql

# Восстановить из бэкапа
docker-compose exec -T db psql -U ascouser ascodb < backup_20250108.sql
```

## 📊 Мониторинг

### Проверка статуса
```bash
docker-compose ps
docker stats
```

### Проверка доступности
```bash
curl -I http://asco.kg
curl -I https://asco.kg
```

## 🐛 Решение проблем

### Проблема: Контейнеры не запускаются
```bash
docker-compose logs
docker-compose down
docker-compose up -d --build
```

### Проблема: База данных не подключается
- Проверьте .env файл
- Проверьте логи: `docker-compose logs db`
- Убедитесь, что контейнер db запущен: `docker-compose ps`

### Проблема: Статические файлы не загружаются
```bash
docker-compose exec web python manage.py collectstatic --noinput
docker-compose restart nginx
```

### Проблема: 502 Bad Gateway
- Проверьте, что Django контейнер запущен: `docker-compose ps`
- Проверьте логи Django: `docker-compose logs web`
- Проверьте, что порт 8000 доступен внутри сети Docker

## 📞 Поддержка

При возникновении проблем проверьте:
1. Логи контейнеров
2. Настройки .env файла
3. DNS записи
4. Firewall правила
5. Статус контейнеров: `docker-compose ps`

