#!/usr/bin/env bash
# =============================================================================
# AI Backoffice MVP — Reset Database (LOCAL DEV ONLY)
# Drops and recreates the schema, then re-applies all migrations.
# ⚠  WARNING: This destroys ALL data. Never run against production.
# =============================================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}⚠  WARNING: This will DROP all tables and re-run migrations.${NC}"
echo -e "${YELLOW}   Intended for local development only.${NC}"
echo ""
read -r -p "Type 'yes' to confirm: " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
  echo "Aborted."
  exit 0
fi

echo -e "\n${RED}Dropping schema...${NC}"
docker compose exec db psql -U backoffice -d backoffice \
  -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

echo -e "\n${GREEN}Re-applying migrations...${NC}"
docker compose exec app alembic upgrade head

echo -e "\n${GREEN}✓ Database reset complete.${NC}"
