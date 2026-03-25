#!/bin/bash
# ═══════════════════════════════════════════════════════
#  SafeStep — One-Command Setup (Mac / Linux)
#  Run: bash start.sh
# ═══════════════════════════════════════════════════════

set -e  # exit on any error

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # no color

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   🦶  SafeStep Backend Setup             ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
echo ""

# ── Check Python ────────────────────────────────────────
echo -e "${YELLOW}▶ Checking Python...${NC}"
if ! command -v python3 &>/dev/null; then
  echo -e "${RED}✗ Python 3 not found. Install from https://python.org${NC}"
  exit 1
fi
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"

# ── Create virtual environment ──────────────────────────
echo -e "${YELLOW}▶ Creating virtual environment...${NC}"
python3 -m venv venv
echo -e "${GREEN}✓ Virtual environment created${NC}"

# ── Activate venv ───────────────────────────────────────
source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# ── Install dependencies ────────────────────────────────
echo -e "${YELLOW}▶ Installing dependencies (this takes ~30 seconds)...${NC}"
pip install -q -r requirements.txt
echo -e "${GREEN}✓ All dependencies installed${NC}"

# ── Create .env if it doesn't exist ────────────────────
if [ ! -f .env ]; then
  echo -e "${YELLOW}▶ Creating .env from template...${NC}"
  cp .env.example .env
  # Generate a random secret key
  SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
  sed -i.bak "s/safestep_super_secret_key_change_this_256bits_minimum/$SECRET/" .env
  rm -f .env.bak
  echo -e "${GREEN}✓ .env created with auto-generated secret key${NC}"
else
  echo -e "${GREEN}✓ .env already exists — skipping${NC}"
fi

# ── Create db directory ─────────────────────────────────
mkdir -p db

# ── Done — launch server ────────────────────────────────
echo ""
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅  Setup complete! Starting server...   ${NC}"
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}  Website:   http://localhost:8000${NC}"
echo -e "${BLUE}  API Docs:  http://localhost:8000/api/docs${NC}"
echo ""
echo -e "  Press ${YELLOW}Ctrl+C${NC} to stop the server"
echo ""

uvicorn main:app --reload --host 0.0.0.0 --port 8000
