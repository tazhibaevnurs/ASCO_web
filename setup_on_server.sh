#!/bin/bash
set -e

echo "🚀 Настройка сервера для ASCO.KG"

# Создаем директорию /var/www если её нет
if [ ! -d "/var/www" ]; then
    echo "📁 Создаем директорию /var/www..."
    mkdir -p /var/www
fi

# Переходим в директорию
cd /var/www

# Клонируем репозиторий
if [ ! -d "ASCO_web" ]; then
    echo "📥 Клонируем репозиторий..."
    git clone https://github.com/tazhibaevnurs/ASCO_web.git
    cd ASCO_web
else
    echo "⚠️  Директория ASCO_web уже существует"
    cd ASCO_web
    echo "🔄 Обновляем репозиторий..."
    git pull origin master
fi

echo "✅ Готово! Теперь выполните:"
echo "1. cd /var/www/ASCO_web"
echo "2. Создайте .env файл"
echo "3. Запустите ./deploy.sh"

