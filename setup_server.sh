#!/bin/bash
set -e

echo "🔧 Setting up server for ASCO.KG deployment..."

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Update system
echo -e "${BLUE}📦 Updating system packages...${NC}"
apt update && apt upgrade -y

# Install Docker
if ! command -v docker &> /dev/null; then
    echo -e "${BLUE}🐳 Installing Docker...${NC}"
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
else
    echo -e "${GREEN}✅ Docker already installed${NC}"
fi

# Install Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${BLUE}📦 Installing Docker Compose...${NC}"
    apt install docker-compose -y
else
    echo -e "${GREEN}✅ Docker Compose already installed${NC}"
fi

# Install Git
if ! command -v git &> /dev/null; then
    echo -e "${BLUE}📦 Installing Git...${NC}"
    apt install git -y
else
    echo -e "${GREEN}✅ Git already installed${NC}"
fi

# Install Certbot
if ! command -v certbot &> /dev/null; then
    echo -e "${BLUE}🔒 Installing Certbot...${NC}"
    apt install certbot -y
else
    echo -e "${GREEN}✅ Certbot already installed${NC}"
fi

# Install additional tools
echo -e "${BLUE}📦 Installing additional tools...${NC}"
apt install -y curl wget nano ufw

# Setup firewall
echo -e "${BLUE}🔥 Configuring firewall...${NC}"
ufw --force enable
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw status

# Create project directory
echo -e "${BLUE}📁 Creating project directory...${NC}"
mkdir -p /var/www
cd /var/www

# Clone repository if not exists
if [ ! -d "ASCO_web" ]; then
    echo -e "${BLUE}📥 Cloning repository...${NC}"
    git clone https://github.com/tazhibaevnurs/ASCO_web.git
else
    echo -e "${YELLOW}⚠️  Directory ASCO_web already exists${NC}"
fi

cd ASCO_web

# Create necessary directories
echo -e "${BLUE}📁 Creating necessary directories...${NC}"
mkdir -p logs nginx/ssl certbot/conf certbot/www

# Make scripts executable
chmod +x deploy.sh 2>/dev/null || true

echo -e "${GREEN}✅ Server setup complete!${NC}"
echo ""
echo -e "${YELLOW}📋 Next steps:${NC}"
echo "1. cd /var/www/ASCO_web"
echo "2. Create .env file with your configuration"
echo "3. Run ./deploy.sh or docker-compose up -d --build"
echo ""
echo -e "${BLUE}💡 To generate SECRET_KEY:${NC}"
echo "python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'"

