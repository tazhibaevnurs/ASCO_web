# 🚀 Быстрый старт - Развертывание ASCO.KG

## 📋 Информация о сервере
- **Сервер:** root@31.207.74.12
- **Домен:** asco.kg, www.asco.kg
- **Репозиторий:** https://github.com/tazhibaevnurs/ASCO_web

## ⚡ Быстрое развертывание (5 минут)

### 1. Подключитесь к серверу
```bash
ssh root@31.207.74.12
```

### 2. Запустите автоматическую настройку
```bash
cd /var/www
wget https://raw.githubusercontent.com/tazhibaevnurs/ASCO_web/master/setup_server.sh
chmod +x setup_server.sh
./setup_server.sh
```

Или вручную:
```bash
cd /var/www
git clone https://github.com/tazhibaevnurs/ASCO_web.git
cd ASCO_web
```

### 3. Создайте .env файл
```bash
nano .env
```

Вставьте (обязательно измените пароли!):
```env
SECRET_KEY=сгенерируйте-новый-ключ
DEBUG=False
ALLOWED_HOSTS=asco.kg,www.asco.kg
TIME_ZONE=Asia/Bishkek
CSRF_TRUSTED_ORIGINS=https://asco.kg,https://www.asco.kg

DB_NAME=ascodb
DB_USER=ascouser
DB_PASSWORD=надежный-пароль
DB_HOST=db
DB_PORT=5432

POSTGRES_DB=ascodb
POSTGRES_USER=ascouser
POSTGRES_PASSWORD=надежный-пароль
```

**Генерация SECRET_KEY:**
```bash
python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

### 4. Запустите развертывание
```bash
chmod +x deploy.sh
./deploy.sh
```

Или вручную:
```bash
mkdir -p logs nginx/ssl certbot/conf certbot/www
docker-compose up -d --build
sleep 15
docker-compose exec web python manage.py migrate --noinput
docker-compose exec web python manage.py collectstatic --noinput
```

### 5. Создайте суперпользователя
```bash
docker-compose exec web python manage.py createsuperuser
```

### 6. Настройте SSL (опционально, но рекомендуется)

```bash
# Остановите nginx
docker-compose stop nginx

# Получите сертификат
certbot certonly --standalone \
  --email your-email@example.com \
  --agree-tos \
  --no-eff-email \
  -d asco.kg \
  -d www.asco.kg

# Скопируйте сертификаты
cp /etc/letsencrypt/live/asco.kg/fullchain.pem nginx/ssl/
cp /etc/letsencrypt/live/asco.kg/privkey.pem nginx/ssl/

# Используйте HTTPS конфигурацию
cp nginx-https.conf nginx.conf

# Запустите nginx
docker-compose up -d nginx
```

## ✅ Проверка

```bash
# Проверьте статус контейнеров
docker-compose ps

# Проверьте логи
docker-compose logs -f

# Проверьте доступность
curl -I http://asco.kg
```

## 🔄 Обновление проекта

```bash
cd /var/www/ASCO_web
git pull origin master
docker-compose up -d --build
docker-compose exec web python manage.py migrate --noinput
docker-compose exec web python manage.py collectstatic --noinput
docker-compose restart
```

## 📞 Полезные команды

```bash
# Логи
docker-compose logs -f web
docker-compose logs -f nginx

# Перезапуск
docker-compose restart web
docker-compose restart nginx

# Остановка
docker-compose down

# Запуск
docker-compose up -d
```

## 🐛 Решение проблем

**Контейнеры не запускаются:**
```bash
docker-compose logs
docker-compose down
docker-compose up -d --build
```

**База данных:**
```bash
docker-compose logs db
docker-compose restart db
```

**Статические файлы:**
```bash
docker-compose exec web python manage.py collectstatic --noinput
docker-compose restart nginx
```

---

📖 **Полная документация:** См. `DEPLOYMENT_GUIDE.md`

