#!/bin/bash
# ═══════════════════════════════════════════════════════════
#  TrackWise Backend — Local Setup Script
#  Run once to get the dev environment ready.
#  Usage: bash scripts/setup.sh
# ═══════════════════════════════════════════════════════════

set -e  # Exit on error
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}  TrackWise Backend — Setup${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"

# ── 1. Check Python ───────────────────────────────────────
echo -e "\n${YELLOW}[1/7] Checking Python version...${NC}"
python3 --version
if ! python3 -c "import sys; assert sys.version_info >= (3, 10)" 2>/dev/null; then
  echo -e "${RED}Error: Python 3.10+ is required.${NC}"
  exit 1
fi
echo -e "${GREEN}✓ Python OK${NC}"

# ── 2. Create virtual environment ─────────────────────────
echo -e "\n${YELLOW}[2/7] Creating virtual environment...${NC}"
if [ ! -d "venv" ]; then
  python3 -m venv venv
  echo -e "${GREEN}✓ Virtual environment created${NC}"
else
  echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi

# Activate
source venv/bin/activate

# ── 3. Install dependencies ───────────────────────────────
echo -e "\n${YELLOW}[3/7] Installing dependencies...${NC}"
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo -e "${GREEN}✓ Dependencies installed${NC}"

# ── 4. Setup .env ─────────────────────────────────────────
echo -e "\n${YELLOW}[4/7] Setting up .env file...${NC}"
if [ ! -f ".env" ]; then
  cp .env.example .env
  # Generate a secure secret key
  SECRET=$(python3 -c "from django.utils.crypto import get_random_string; print(get_random_string(50))" 2>/dev/null || python3 -c "import secrets; print(secrets.token_urlsafe(50))")
  sed -i "s/your-secret-key-here-change-in-production/$SECRET/" .env
  echo -e "${GREEN}✓ .env created from .env.example with generated SECRET_KEY${NC}"
  echo -e "${YELLOW}  → Edit .env to add your database credentials${NC}"
else
  echo -e "${GREEN}✓ .env already exists${NC}"
fi

# ── 5. Create logs directory ──────────────────────────────
echo -e "\n${YELLOW}[5/7] Creating directories...${NC}"
mkdir -p logs staticfiles media
echo -e "${GREEN}✓ Directories ready${NC}"

# ── 6. Database setup ─────────────────────────────────────
echo -e "\n${YELLOW}[6/7] Running database migrations...${NC}"
export DJANGO_SETTINGS_MODULE=trackwise_backend.settings.development
python3 manage.py makemigrations accounts expenses learning goals savings subscriptions dashboard
python3 manage.py migrate
echo -e "${GREEN}✓ Database migrated${NC}"

# ── 7. Create superuser (optional) ────────────────────────
echo -e "\n${YELLOW}[7/7] Create admin superuser? (y/N)${NC}"
read -r CREATE_SUPER
if [[ "$CREATE_SUPER" =~ ^[Yy]$ ]]; then
  python3 manage.py createsuperuser
fi

echo ""
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}  Setup complete! 🎉${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo ""
echo -e "Start the dev server:"
echo -e "  ${YELLOW}source venv/bin/activate${NC}"
echo -e "  ${YELLOW}python manage.py runserver${NC}"
echo ""
echo -e "API base URL: ${YELLOW}http://localhost:8000/api/v1/${NC}"
echo -e "Admin panel:  ${YELLOW}http://localhost:8000/admin/${NC}"
echo -e "Health check: ${YELLOW}http://localhost:8000/health/${NC}"
