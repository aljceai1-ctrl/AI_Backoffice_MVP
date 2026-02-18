# AI Backoffice MVP

> Local invoice-processing system for Dubai SMEs / property management.
> Upload → Extract → Validate → Human Approval → CSV Export. **No autopay.**

---

## Quickstart

**Prerequisites**

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) running (includes `docker compose` v2)
- macOS or Linux shell (bash or zsh — see zsh tips below)
- `make` (pre-installed on macOS via Xcode CLT; `sudo apt install make` on Ubuntu)

**Four commands to a running system**

```bash
cd ~/Desktop/AI_Backoffice_MVP
make up        # build images + start postgres + app  (~60 s first run)
make migrate   # apply Alembic migrations to postgres
make test      # run end-to-end smoke test (all 8 checks must pass)
open http://localhost:8000/docs   # interactive API explorer
```

Expected outcome after `make test`:

```
── Step 1/8  Health check
  ✓  GET /health → {"status":"ok"}
── Step 2/8  Upload invoice
  ✓  POST /invoices/upload → id=<uuid>  status=NEW
── Step 3/8  Extract fields
  ✓  POST /invoices/<uuid>/extract → status=EXTRACTED
── Step 4/8  Validate
  ✓  POST /invoices/<uuid>/validate → status=VALIDATED
── Step 5/8  Approve
  ✓  POST /invoices/<uuid>/approve → decision=APPROVE
  ✓  GET /invoices/<uuid> → status=APPROVED
── Step 6/8  Payment pack CSV
  ✓  GET /payment-pack.csv → contains approved invoice
── Step 7/8  Weekly pack Markdown
  ✓  GET /weekly-pack.md → Markdown report returned
── Step 8/8  Audit log
  ✓  GET /audit?limit=20 → N event(s) returned

  PASSED  8 / 8 checks
```

---

## Make targets

| Command | What it does |
|---------|-------------|
| `make up` | `docker compose up -d --build` |
| `make migrate` | `docker compose exec app alembic upgrade head` |
| `make test` | Runs `scripts/smoke_test.sh` against `http://localhost:8000` |
| `make logs` | `docker compose logs -f --tail=200` |
| `make down` | `docker compose down -v` (removes containers **and** volumes) |
| `make shell` | bash shell inside the app container |
| `make psql` | psql inside the db container |

---

## API reference

All endpoints except `GET /health` require the header `X-API-Key: <value>`.
The key is set in `.env` as `BACKOFFICE_API_KEY`.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness probe (no auth) |
| POST | `/invoices/upload` | Upload invoice file (multipart) |
| POST | `/invoices/{id}/extract` | Apply structured fields |
| POST | `/invoices/{id}/validate` | Run validation rules |
| POST | `/invoices/{id}/approve` | Human APPROVE / REJECT |
| GET | `/invoices` | List with optional `status` / date filters |
| GET | `/invoices/{id}` | Detail + exceptions + approvals |
| GET | `/payment-pack.csv` | Export approved invoices (date range) |
| GET | `/weekly-pack.md` | Weekly finance ops report |
| GET | `/audit` | Immutable audit trail |

**Demo curl sequence** (replace `$ID` with the returned UUID):

```bash
KEY="dev-api-key-change-me"
BASE="http://localhost:8000"

# Upload
ID=$(curl -s -X POST "$BASE/invoices/upload" \
  -H "X-API-Key: $KEY" \
  -F "file=@test_data/sample_invoice.txt" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")

# Extract
curl -s -X POST "$BASE/invoices/$ID/extract" \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"vendor":"ACME","invoice_number":"INV-001","invoice_date":"2024-06-01","due_date":"2024-06-30","amount":10000,"currency":"AED"}'

# Validate
curl -s -X POST "$BASE/invoices/$ID/validate" -H "X-API-Key: $KEY"

# Approve
curl -s -X POST "$BASE/invoices/$ID/approve" \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"decision":"APPROVE","decided_by":"Finance Manager","notes":"OK"}'

# Export CSV
curl -s "$BASE/payment-pack.csv?from=2024-01-01&to=2024-12-31" -H "X-API-Key: $KEY"

# Audit trail
curl -s "$BASE/audit?limit=20" -H "X-API-Key: $KEY" | python3 -m json.tool
```

---

## Environment variables

Copy `.env.example` → `.env` to override defaults:

```bash
cp .env.example .env
```

| Variable | Default | Notes |
|----------|---------|-------|
| `BACKOFFICE_API_KEY` | `dev-api-key-change-me` | **Change before any non-local use** |
| `DATABASE_URL` | `postgresql://…@localhost:5432/…` | Overridden inside Docker to `@db:5432` |
| `UPLOAD_DIR` | `./data/uploads` | Overridden inside Docker to `/app/data/uploads` |
| `ALLOWED_CURRENCIES` | `["AED","USD","EUR"]` | JSON array string |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## Troubleshooting

### "Cannot connect to the Docker daemon" / Docker not running

```bash
open -a Docker          # macOS: start Docker Desktop
# wait ~15 s, then:
make up
```

### Ports 8000 or 5432 already in use

```bash
# Find what's on the port:
lsof -i :8000
lsof -i :5432

# Kill it, or change the host port in docker-compose.yml:
#   ports:
#     - "8001:8000"   ← change left side only
```

### `relation "invoices" does not exist` (or any 503 from the API)

Migrations have not been applied. Run:

```bash
make migrate
```

The app now returns a friendly 503 with the hint message if this happens at
runtime, and logs a prominent warning box at startup.

### `make test` fails with "connection error" on step 1

The app container may still be starting. Check its status:

```bash
make logs          # look for "Application startup complete"
docker compose ps  # app should show "running"
```

If it shows "restarting", there is likely a Python error — `make logs` will
show the traceback.

### zsh-specific pitfalls

- **Never prepend `~` to `docker`** — `~docker` means "home directory of user
  docker" in zsh and will fail with a confusing error.
- **Bracketed paste mode** can inject `^[[200~` / `^[[201~` characters at the
  start/end of a pasted block. If a command fails with `zsh: command not found:
  ^[[200~docker`, paste it into a plain text editor first, then run it.
- **Long multi-line curl commands** pasted directly into zsh can lose newlines
  or misparse quoting. For complex sequences, run them as a bash script:
  ```bash
  bash -c 'curl -s http://localhost:8000/health'
  ```
- **History expansion**: if your API key or JSON contains `!`, wrap the
  argument in single quotes or use `set +H` first.

### Completely reset local state

```bash
make down          # removes containers + postgres volume
make up            # rebuild from scratch
make migrate       # re-apply migrations
make test          # verify everything works
```

---

## Project layout

```
AI_Backoffice_MVP/
├── app/
│   ├── main.py              FastAPI app, lifespan, error handlers
│   ├── core/                settings, auth, logging, middleware
│   ├── db/                  engine, session, base
│   ├── models/              SQLAlchemy ORM (invoice, exception, approval, audit)
│   ├── schemas/             Pydantic v2 request/response models
│   ├── api/routers/         health, invoices, exports, audit
│   └── services/            storage, extraction*, validation, approval,
│                            exports, reporting, audit
├── alembic/                 migrations (001_initial_schema.py)
├── tests/                   pytest suite (requires db_test on :5433)
├── test_data/               sample_invoice.txt — used by smoke_test.sh
├── scripts/
│   ├── smoke_test.sh        end-to-end demo test (make test)
│   ├── bootstrap.sh         all-in-one first-run helper
│   └── reset_db.sh          drop + recreate schema (dev only)
├── data/uploads/            invoice file storage (gitignored)
├── Makefile
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

\* `app/services/extraction.py` contains the marked integration point for
LLM/OCR extraction. See that file for instructions.

---

## Running pytest (optional)

The pytest suite uses a separate Postgres instance on port 5433 (`db_test`).
Both database containers must be running:

```bash
make up    # starts both db and db_test

docker compose exec \
  -e TEST_DATABASE_URL="postgresql://backoffice:backoffice@db_test:5432/backoffice_test" \
  app pytest tests/ -v
```

---

*Built with Python 3.12 · FastAPI 0.111 · SQLAlchemy 2.0 · Alembic · Pydantic v2 · PostgreSQL 16*
