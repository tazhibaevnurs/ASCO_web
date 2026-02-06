#!/bin/bash
set -e

echo "🚀 Starting deployment process..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from template...${NC}"
    cat > .env << EOF
# Django Settings
SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
DEBUG=False
ALLOWED_HOSTS=asco.kg,www.asco.kg
TIME_ZONE=Asia/Bishkek
CSRF_TRUSTED_ORIGINS=https://asco.kg,https://www.asco.kg

# Database Configuration
DB_NAME=ascodb
DB_USER=ascouser
DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
DB_HOST=db
DB_PORT=5432

# PostgreSQL (for docker-compose)
POSTGRES_DB=ascodb
POSTGRES_USER=ascouser
POSTGRES_PASSWORD=\${DB_PASSWORD}
EOF
    echo -e "${GREEN}✅ .env file created. Please review and update if needed.${NC}"
    echo -e "${YELLOW}⚠️  IMPORTANT: Update DB_PASSWORD and POSTGRES_PASSWORD with a secure password!${NC}"
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p logs
mkdir -p nginx/ssl
mkdir -p certbot/conf
mkdir -p certbot/www

# Stop existing containers (БЕЗ -v: тома postgres_data, media, static НЕ удаляются)
echo "🛑 Stopping existing containers..."
docker-compose down || true

# Build and start containers
echo "🔨 Building and starting containers..."
docker-compose up -d --build

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
sleep 10

# Run migrations
echo "📊 Running database migrations..."
docker-compose exec -T web python manage.py migrate --noinput

# Collect static files
echo "📦 Collecting static files..."
docker-compose exec -T web python manage.py collectstatic --noinput

# Create superuser (optional)
echo -e "${YELLOW}💡 To create a superuser, run:${NC}"
echo "docker-compose exec web python manage.py createsuperuser"

echo -e "${GREEN}✅ Deployment complete!${NC}"
echo -e "${GREEN}🌐 Your application should be available at http://asco.kg${NC}"
echo ""
echo "📋 Useful commands:"
echo "  - View logs: docker-compose logs -f"
echo "  - Stop: docker-compose down"
echo "  - Restart: docker-compose restart"
echo "  - Shell access: docker-compose exec web bash"

