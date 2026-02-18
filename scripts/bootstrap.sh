#!/usr/bin/env bash
# =============================================================================
# AI Backoffice MVP — Bootstrap Script
# Verifies Docker, starts services, runs migrations, tests, and a smoke test.
# =============================================================================
set -euo pipefail

CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Colour

section() { echo -e "\n${CYAN}▶ $1${NC}"; }
ok()      { echo -e "${GREEN}✓ $1${NC}"; }
warn()    { echo -e "${YELLOW}⚠ $1${NC}"; }
fail()    { echo -e "${RED}✗ $1${NC}"; exit 1; }

BASE_URL="http://localhost:8000"
API_KEY="${BACKOFFICE_API_KEY:-dev-api-key-change-me}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# ─── 1. Verify Docker ─────────────────────────────────────────────────────────
section "Checking Docker"
if ! docker info > /dev/null 2>&1; then
  fail "Docker is not running. Start Docker Desktop and re-run this script."
fi
ok "Docker is running"

# ─── 2. Copy .env if missing ──────────────────────────────────────────────────
section "Environment"
if [ ! -f "$PROJECT_DIR/.env" ]; then
  cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
  warn ".env created from .env.example — review BACKOFFICE_API_KEY before production use"
else
  ok ".env exists"
fi

# ─── 3. Build and start services ─────────────────────────────────────────────
section "Starting Docker services (build + up)"
cd "$PROJECT_DIR"
docker compose up -d --build
ok "Services started"

# ─── 4. Wait for DB + app to be healthy ──────────────────────────────────────
section "Waiting for app to be ready"
MAX_WAIT=60
ELAPSED=0
until curl -sf "$BASE_URL/health" > /dev/null 2>&1; do
  if [ $ELAPSED -ge $MAX_WAIT ]; then
    fail "App did not become ready within ${MAX_WAIT}s. Check: docker compose logs app"
  fi
  sleep 2
  ELAPSED=$((ELAPSED + 2))
done
ok "App is healthy at $BASE_URL"

# ─── 5. Run Alembic migrations ────────────────────────────────────────────────
section "Running database migrations"
docker compose exec app alembic upgrade head
ok "Migrations applied"

# ─── 6. Run test suite ────────────────────────────────────────────────────────
section "Running pytest"
docker compose exec -e TEST_DATABASE_URL="postgresql://backoffice:backoffice@db_test:5432/backoffice_test" \
  app pytest tests/ -v --tb=short
ok "All tests passed"

# ─── 7. Smoke test sequence ───────────────────────────────────────────────────
section "Smoke test (full invoice lifecycle)"

echo "  [1/7] GET /health"
curl -sf "$BASE_URL/health" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['status']=='ok'"
ok "  Health OK"

echo "  [2/7] POST /invoices/upload"
echo "DUMMY INVOICE CONTENT" > /tmp/_smoke_invoice.txt
UPLOAD=$(curl -sf -X POST "$BASE_URL/invoices/upload" \
  -H "X-API-Key: $API_KEY" \
  -F "file=@/tmp/_smoke_invoice.txt;type=text/plain")
INVOICE_ID=$(echo "$UPLOAD" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "     Invoice ID: $INVOICE_ID"
ok "  Upload OK"

echo "  [3/7] POST /invoices/{id}/extract"
curl -sf -X POST "$BASE_URL/invoices/$INVOICE_ID/extract" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "vendor": "Smoke Test Corp",
    "invoice_number": "SMOKE-001",
    "invoice_date": "2024-06-01",
    "due_date": "2024-07-01",
    "amount": 25000.00,
    "currency": "AED"
  }' > /dev/null
ok "  Extract OK"

echo "  [4/7] POST /invoices/{id}/validate"
VALIDATE=$(curl -sf -X POST "$BASE_URL/invoices/$INVOICE_ID/validate" \
  -H "X-API-Key: $API_KEY")
STATUS=$(echo "$VALIDATE" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
echo "     Status after validation: $STATUS"
ok "  Validate OK"

echo "  [5/7] POST /invoices/{id}/approve"
curl -sf -X POST "$BASE_URL/invoices/$INVOICE_ID/approve" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"decision": "APPROVE", "decided_by": "Bootstrap Script", "notes": "Smoke test approval"}' > /dev/null
ok "  Approve OK"

echo "  [6/7] GET /payment-pack.csv"
TODAY=$(date +%Y-%m-%d)
YEAR_AGO=$(date -d "1 year ago" +%Y-%m-%d 2>/dev/null || date -v-1y +%Y-%m-%d)
CSV=$(curl -sf "$BASE_URL/payment-pack.csv?from=$YEAR_AGO&to=$TODAY" \
  -H "X-API-Key: $API_KEY")
echo "$CSV" | grep -q "Smoke Test Corp" && ok "  Payment pack contains approved invoice" || warn "  Payment pack returned (check date range)"

echo "  [7/7] GET /weekly-pack.md"
WEEK_START=$(date +%Y-%m-%d)
curl -sf "$BASE_URL/weekly-pack.md?week_start=$WEEK_START" \
  -H "X-API-Key: $API_KEY" | grep -q "Weekly Finance Ops Pack"
ok "  Weekly pack OK"

# ─── Done ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  AI Backoffice MVP bootstrap complete!              ${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
echo ""
echo "  API Docs:   $BASE_URL/docs"
echo "  API Key:    $API_KEY"
echo "  Invoice ID: $INVOICE_ID  (now APPROVED)"
echo ""
echo "  Next steps:"
echo "    curl -H 'X-API-Key: $API_KEY' '$BASE_URL/invoices'"
echo "    curl -H 'X-API-Key: $API_KEY' '$BASE_URL/audit'"
echo ""
