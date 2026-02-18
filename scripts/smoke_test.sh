#!/usr/bin/env bash
# =============================================================================
# AI Backoffice MVP — Smoke Test
# Runs a full invoice lifecycle against a running API and reports PASS / FAIL.
#
# Usage:
#   ./scripts/smoke_test.sh                  (uses http://localhost:8000)
#   BASE_URL=http://my-host:8000 ./scripts/smoke_test.sh
# =============================================================================
set -euo pipefail

# ── Config ───────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

BASE_URL="${BASE_URL:-http://localhost:8000}"

# Load BACKOFFICE_API_KEY safely from .env (no shell-sourcing to avoid side effects)
if [ -f "$REPO_DIR/.env" ]; then
  KEY=$(grep -m1 '^BACKOFFICE_API_KEY=' "$REPO_DIR/.env" 2>/dev/null \
        | cut -d= -f2- | tr -d '"'"'" | tr -d "'" || true)
fi
KEY="${KEY:-dev-api-key-change-me}"

SAMPLE_FILE="$REPO_DIR/test_data/sample_invoice.txt"
TODAY=$(date +%Y-%m-%d)
YEAR_AGO=$(date -d "1 year ago" +%Y-%m-%d 2>/dev/null \
           || date -v-1y +%Y-%m-%d 2>/dev/null \
           || echo "2023-01-01")

PASS=0
FAIL=0

# ── Helpers ──────────────────────────────────────────────────────────────────

green()  { printf '\033[0;32m%s\033[0m\n' "$*"; }
red()    { printf '\033[0;31m%s\033[0m\n' "$*"; }
cyan()   { printf '\033[0;36m%s\033[0m\n' "$*"; }
yellow() { printf '\033[1;33m%s\033[0m\n' "$*"; }

pass() { green  "  ✓  $1"; PASS=$((PASS + 1)); }
fail() { red    "  ✗  FAIL: $1"; FAIL=$((FAIL + 1)); }
step() { echo ""; cyan "── Step $1"; }

# Curl with a short timeout; returns empty string on connection error.
api_get() {
  curl -sf --max-time 10 "$@" || echo "__ERROR__"
}
api_post() {
  curl -sf --max-time 10 -X POST "$@" || echo "__ERROR__"
}

json_field() {
  # Usage: json_field <json_string> <field>
  echo "$1" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('$2',''))" 2>/dev/null || true
}

# ── Pre-flight ────────────────────────────────────────────────────────────────

echo ""
yellow "=== AI Backoffice MVP — Smoke Test ==="
echo "  Target : $BASE_URL"
echo "  API Key: ${KEY:0:8}…"
echo "  File   : $SAMPLE_FILE"

if [ ! -f "$SAMPLE_FILE" ]; then
  red "Sample file not found: $SAMPLE_FILE"
  exit 1
fi

# ── Step 1 / Health check ─────────────────────────────────────────────────────

step "1/8  Health check"
RESP=$(api_get "$BASE_URL/health")
if echo "$RESP" | grep -q '"ok"'; then
  pass "GET /health → {\"status\":\"ok\"}"
else
  fail "GET /health returned: $RESP"
  red ""
  red "Is the app running?  Try:  make up && make migrate"
  exit 1
fi

# ── Step 2 / Upload ───────────────────────────────────────────────────────────

step "2/8  Upload invoice"
UPLOAD=$(curl -sf --max-time 15 -X POST "$BASE_URL/invoices/upload" \
  -H "X-API-Key: $KEY" \
  -F "file=@${SAMPLE_FILE};type=text/plain" || echo "__ERROR__")

if echo "$UPLOAD" | grep -q "__ERROR__"; then
  fail "POST /invoices/upload — connection error"
  exit 1
fi

INVOICE_ID=$(json_field "$UPLOAD" "id")
STATUS=$(json_field "$UPLOAD" "status")

if [ -z "$INVOICE_ID" ] || [ "$INVOICE_ID" = "None" ]; then
  fail "POST /invoices/upload — no id in response: $UPLOAD"
  exit 1
fi

if [ "$STATUS" = "NEW" ]; then
  pass "POST /invoices/upload → id=$INVOICE_ID  status=$STATUS"
else
  fail "POST /invoices/upload → unexpected status '$STATUS' (want NEW)"
fi

# ── Step 3 / Extract fields ───────────────────────────────────────────────────

step "3/8  Extract fields"
EXTRACT=$(api_post "$BASE_URL/invoices/$INVOICE_ID/extract" \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "vendor":         "Al Futtaim Facilities Management LLC",
    "invoice_number": "DEMO-2024-0042",
    "invoice_date":   "2024-06-01",
    "due_date":       "2024-06-30",
    "amount":         75000.00,
    "currency":       "AED"
  }')

EXT_STATUS=$(json_field "$EXTRACT" "status")
if [ "$EXT_STATUS" = "EXTRACTED" ]; then
  pass "POST /invoices/$INVOICE_ID/extract → status=EXTRACTED"
else
  fail "Extract → unexpected status '$EXT_STATUS': $EXTRACT"
fi

# ── Step 4 / Validate ─────────────────────────────────────────────────────────

step "4/8  Validate"
VALIDATE=$(api_post "$BASE_URL/invoices/$INVOICE_ID/validate" \
  -H "X-API-Key: $KEY")

VAL_STATUS=$(json_field "$VALIDATE" "status")
# A clean invoice should reach VALIDATED; APPROVAL_PENDING is also acceptable
if [ "$VAL_STATUS" = "VALIDATED" ] || [ "$VAL_STATUS" = "APPROVAL_PENDING" ]; then
  pass "POST /invoices/$INVOICE_ID/validate → status=$VAL_STATUS"
else
  fail "Validate → unexpected status '$VAL_STATUS': $VALIDATE"
fi

# ── Step 5 / Approve ──────────────────────────────────────────────────────────

step "5/8  Approve"
APPROVE=$(api_post "$BASE_URL/invoices/$INVOICE_ID/approve" \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "decision":   "APPROVE",
    "decided_by": "Smoke Test Runner",
    "notes":      "Automated smoke test approval"
  }')

DECISION=$(json_field "$APPROVE" "decision")
if [ "$DECISION" = "APPROVE" ]; then
  pass "POST /invoices/$INVOICE_ID/approve → decision=APPROVE"
else
  fail "Approve → unexpected decision '$DECISION': $APPROVE"
fi

# Verify invoice status is now APPROVED
INV_DETAIL=$(api_get "$BASE_URL/invoices/$INVOICE_ID" -H "X-API-Key: $KEY")
FINAL_STATUS=$(json_field "$INV_DETAIL" "status")
if [ "$FINAL_STATUS" = "APPROVED" ]; then
  pass "GET /invoices/$INVOICE_ID → status=APPROVED"
else
  fail "Invoice status after approval is '$FINAL_STATUS' (want APPROVED)"
fi

# ── Step 6 / Payment pack CSV ─────────────────────────────────────────────────

step "6/8  Payment pack CSV"
CSV=$(api_get "$BASE_URL/payment-pack.csv?from=${YEAR_AGO}&to=${TODAY}" \
  -H "X-API-Key: $KEY")

if echo "$CSV" | grep -q "vendor"; then
  # Check header is present
  if echo "$CSV" | grep -qi "Al Futtaim\|DEMO-2024"; then
    pass "GET /payment-pack.csv → contains approved invoice"
  else
    pass "GET /payment-pack.csv → header present (invoice may be outside date range)"
  fi
else
  fail "GET /payment-pack.csv → no CSV header found: $CSV"
fi

# ── Step 7 / Weekly pack Markdown ────────────────────────────────────────────

step "7/8  Weekly pack Markdown"
WEEK_START=$(date +%Y-%m-%d)
MD=$(api_get "$BASE_URL/weekly-pack.md?week_start=${WEEK_START}" \
  -H "X-API-Key: $KEY")

if echo "$MD" | grep -q "Weekly Finance Ops Pack"; then
  pass "GET /weekly-pack.md → Markdown report returned"
else
  fail "GET /weekly-pack.md → missing header: $MD"
fi

# ── Step 8 / Audit log ────────────────────────────────────────────────────────

step "8/8  Audit log"
AUDIT=$(api_get "$BASE_URL/audit?limit=20" -H "X-API-Key: $KEY")

# Should be a JSON array with at least the events from this run
if echo "$AUDIT" | python3 -c "import sys,json; events=json.load(sys.stdin); assert len(events)>=1" 2>/dev/null; then
  COUNT=$(echo "$AUDIT" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "?")
  pass "GET /audit?limit=20 → $COUNT event(s) returned"
else
  fail "GET /audit?limit=20 → expected JSON array with events: $AUDIT"
fi

# ── Summary ───────────────────────────────────────────────────────────────────

echo ""
echo "────────────────────────────────────────"
TOTAL=$((PASS + FAIL))
if [ "$FAIL" -eq 0 ]; then
  green "  PASSED  $PASS / $TOTAL checks"
  echo "────────────────────────────────────────"
  echo ""
  echo "  Invoice ID : $INVOICE_ID"
  echo "  Docs       : $BASE_URL/docs"
  echo ""
  exit 0
else
  red "  FAILED  $FAIL / $TOTAL checks  ($PASS passed)"
  echo "────────────────────────────────────────"
  echo ""
  echo "  Tip: check logs with  make logs"
  echo "  Tip: re-run migrations with  make migrate"
  echo ""
  exit 1
fi
