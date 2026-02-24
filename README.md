# AI Backoffice MVP

> Multi-tenant invoice management system with email ingestion, RBAC, dashboards, and analytics.

---

## Quickstart

**Prerequisites:** Docker Desktop running, `make`, and a shell (bash/zsh).

```bash
cd ~/Desktop/AI_Backoffice_MVP
make up      # builds + starts: postgres, mailhog, backend, frontend
```

Wait ~90 seconds for first build. Then:

- **Frontend:** http://localhost:3000
- **Backend API docs:** http://localhost:8000/docs
- **MailHog (email):** http://localhost:8025

The backend auto-runs migrations and seeds demo data on first start.

---

## Demo Logins

All passwords: **`demo1234`**

| Email | Role | Tenant |
|-------|------|--------|
| `admin@acme.local` | ADMIN | Acme Corp |
| `approver@acme.local` | APPROVER | Acme Corp |
| `auditor@acme.local` | AUDITOR | Acme Corp |
| `uploader@acme.local` | UPLOADER | Acme Corp |
| `viewer@acme.local` | VIEWER | Acme Corp |
| `admin@gulf.local` | ADMIN | Gulf Trading LLC |
| `approver@gulf.local` | APPROVER | Gulf Trading LLC |

---

## Architecture

```
AI_Backoffice_MVP/
├── backend/             Python 3.12 + FastAPI + SQLAlchemy 2.0
│   ├── app/
│   │   ├── api/routers/ auth, users, invoices, payments, audit, analytics, exports, tenants
│   │   ├── core/        config, security (JWT + bcrypt)
│   │   ├── db/          engine, session, base
│   │   ├── models/      8 tables: tenants, users, invoices, payments, exceptions, approvals, audit_events, ingestion_runs
│   │   ├── schemas/     Pydantic v2 request/response models
│   │   ├── services/    validation, audit
│   │   └── workers/     email poller (APScheduler + MailHog)
│   ├── alembic/         migrations
│   ├── scripts/         entrypoint, seed, migrations runner
│   ├── tests/           pytest: auth, RBAC, tenant isolation, invoices, analytics
│   └── Dockerfile
├── frontend/            Next.js 14 + TypeScript + Tailwind + Recharts
│   ├── src/app/         login, dashboard, invoices, invoices/[id], audit, admin/users, admin/settings
│   ├── src/components/  layout (sidebar, auth guard), charts
│   ├── src/lib/         api client, auth context, utils
│   └── Dockerfile
├── docker-compose.yml   postgres, postgres_test, mailhog, backend, frontend
├── Makefile             up, down, seed, migrate, ci, lint, test
├── .github/workflows/   CI: backend quality + tests, frontend lint + build, docker
└── .env.example
```

---

## Make Targets

| Command | Description |
|---------|-------------|
| `make up` | Build and start all services |
| `make down` | Stop and remove containers + volumes |
| `make logs` | Tail container logs |
| `make seed` | Re-run seed script |
| `make migrate` | Run Alembic migrations |
| `make ci` | Full quality gate: lint + format-check + type + pytest |
| `make venv` | Create backend/.venv with all deps |
| `make lint` | ruff check |
| `make format` | ruff format (auto-fix) |
| `make type` | mypy |
| `make pytest` | Run backend tests |
| `make fe-lint` | Run frontend lint |
| `make fe-build` | Build frontend |
| `make test` | Health check (backend + frontend) |
| `make shell` | Bash into backend container |
| `make psql` | psql into postgres |

---

## Core Features

**Authentication & RBAC**
- JWT-based auth with httpOnly cookies + Bearer tokens
- 5 roles: ADMIN, AUDITOR, APPROVER, UPLOADER, VIEWER
- Full tenant isolation (every query scoped by tenant_id)

**Invoice Management**
- Upload PDF/image + metadata
- Automatic validation (required fields, duplicate detection, amount checks, currency validation)
- Status workflow: NEW -> VALIDATED -> APPROVAL_PENDING -> APPROVED -> PAID (or REJECTED)
- Download original files

**Email Ingestion**
- Each tenant gets an inbound email alias (e.g., `acme@inbound.local`)
- APScheduler polls MailHog every 15 seconds
- Automatically creates invoices from email attachments
- Tracks ingestion runs with metrics (processed, failures, retries)

**Dashboards & Analytics**
- Invoice status distribution (pie chart)
- Payments over time, top vendors (bar/line charts)
- Exception rate tracking, top exception codes
- Clean invoice rate, mean time to approval, mean time to resolve
- Ingestion reliability: emails per day, failure rate, retry distribution
- Audit effectiveness: approvals per approver, rejection rate

**Exports**
- Payment pack CSV (date range filter)
- Weekly markdown report

---

## How to Test Email Ingestion Locally

1. Open MailHog: http://localhost:8025
2. Use the MailHog SMTP server (localhost:1025) to send an email:

```bash
# Using swaks (brew install swaks):
swaks --to acme@inbound.local --from test@example.com \
  --server localhost:1025 \
  --attach test_data/sample_invoice.txt \
  --header "Subject: Invoice from vendor"

# Or use any email client configured with SMTP: localhost:1025
```

3. The backend polls MailHog every 15 seconds. Check the invoices list at http://localhost:3000/invoices for the new entry.

---

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/auth/login` | No | Login, returns JWT |
| POST | `/api/auth/logout` | Yes | Clear session |
| GET | `/api/auth/me` | Yes | Current user info |
| GET | `/api/users` | ADMIN | List tenant users |
| POST | `/api/users` | ADMIN | Create user |
| PATCH | `/api/users/{id}` | ADMIN | Update user |
| POST | `/api/invoices/upload` | ADMIN/APPROVER/UPLOADER | Upload invoice |
| GET | `/api/invoices` | Any | List invoices (filters: status, vendor, dates) |
| GET | `/api/invoices/{id}` | Any | Invoice detail |
| GET | `/api/invoices/{id}/download` | Any | Download file |
| POST | `/api/invoices/{id}/approve` | ADMIN/APPROVER | Approve invoice |
| POST | `/api/invoices/{id}/reject` | ADMIN/APPROVER | Reject invoice |
| POST | `/api/invoices/{id}/mark-paid` | ADMIN/APPROVER | Mark as paid |
| GET | `/api/payments` | Any | List payments |
| POST | `/api/payments` | ADMIN/APPROVER | Create payment |
| GET | `/api/audit` | ADMIN/AUDITOR/APPROVER | Audit log |
| GET | `/api/analytics/overview` | Any | Dashboard overview |
| GET | `/api/analytics/payments` | Any | Payment analytics |
| GET | `/api/analytics/effectiveness` | Any | System effectiveness |
| GET | `/api/analytics/ingestion` | Any | Ingestion reliability |
| GET | `/api/analytics/audit-effectiveness` | Any | Audit analytics |
| GET | `/api/exports/payment-pack.csv` | Any | Export payments CSV |
| GET | `/api/exports/weekly-pack.md` | Any | Weekly markdown report |
| GET | `/api/tenants/settings` | ADMIN | Tenant settings |
| PATCH | `/api/tenants/settings` | ADMIN | Update settings |

---

## Environment Variables

See `.env.example` for all variables. Key ones:

| Variable | Default | Notes |
|----------|---------|-------|
| `SECRET_KEY` | dev default | **Change in production** |
| `DATABASE_URL` | postgres://...@localhost:5432/... | Overridden in Docker |
| `MAILHOG_API_URL` | http://localhost:8025/api/v2 | MailHog API |
| `EMAIL_POLL_INTERVAL_SECONDS` | 15 | Email polling frequency |
| `CORS_ORIGINS` | ["http://localhost:3000"] | Allowed CORS origins |

---

## Production Notes

**Email Ingestion Adapters:** The email poller is built with a provider pattern. For production:
- SendGrid Inbound Parse: Implement a webhook handler that receives parsed emails
- AWS SES: Set up an SES receipt rule to invoke a Lambda or push to SQS
- The `MailHogProvider` class in `backend/app/workers/email_poller.py` shows the interface

**Security Checklist:**
- [ ] Change `SECRET_KEY` to a strong random value
- [ ] Use HTTPS in production (set secure cookie flag)
- [ ] Configure proper CORS origins
- [ ] Use a managed Postgres instance
- [ ] Set up S3 for file storage (replace local UPLOAD_DIR)
- [ ] Enable rate limiting in reverse proxy

---

*Built with Python 3.12, FastAPI, SQLAlchemy 2.0, Next.js 14, TypeScript, Tailwind CSS, Recharts, PostgreSQL 16*
