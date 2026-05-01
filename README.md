# SkillBridge Attendance API

A role-based attendance management REST API for a fictional state-level skilling programme. Built with FastAPI, PostgreSQL (Neon), and JWT authentication.

---

## Live API

| Item | Value |
|---|---|
| **Base URL** | `https://skillbridge-api.onrender.com` *(update after deploy)* |
| **Docs (Swagger)** | `https://skillbridge-api.onrender.com/docs` |
| **Health check** | `GET /` |

---

## Local Setup (from scratch)

> Assumes Python 3.11+ and pip are installed. Nothing else required.

```bash
# 1. Clone the repo
git clone https://github.com/YOU/skillbridge.git
cd skillbridge

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and set your DATABASE_URL (Neon connection string)

# 5. Run the server
uvicorn src.main:app --reload

# 6. Seed the database with test data
python seed.py
```

The API is now running at `http://localhost:8000`. Swagger UI is at `http://localhost:8000/docs`.

---

## Test Accounts

All seeded accounts use the password: **`Password123!`**

| Role | Email |
|---|---|
| institution | sunrise@inst.com |
| institution | horizon@inst.com |
| trainer | amit@trainer.com |
| trainer | priya@trainer.com |
| trainer | ravi@trainer.com |
| trainer | sunita@trainer.com |
| programme_manager | deepa@programme.com |
| monitoring_officer | vikram@monitoring.com |
| student | aarav@student.com |

---

## Sample curl Commands

### Auth

```bash
# Signup
curl -X POST https://skillbridge-api.onrender.com/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"name":"Test User","email":"test@test.com","password":"Pass123!","role":"student"}'

# Login (returns JWT)
curl -X POST https://skillbridge-api.onrender.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"aarav@student.com","password":"Password123!"}'

# Get monitoring token (requires monitoring_officer standard JWT + API key)
MONITOR_TOKEN=$(curl -s -X POST https://skillbridge-api.onrender.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"vikram@monitoring.com","password":"Password123!"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -X POST https://skillbridge-api.onrender.com/auth/monitoring-token \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MONITOR_TOKEN" \
  -d '{"key":"sk_monitor_2024_securekey_abc123"}'
```

### Batches

```bash
# Get trainer token
TRAINER_TOKEN=$(curl -s -X POST https://skillbridge-api.onrender.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"amit@trainer.com","password":"Password123!"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Create batch (trainer/institution)
curl -X POST https://skillbridge-api.onrender.com/batches \
  -H "Authorization: Bearer $TRAINER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"New Batch","institution_id":1}'

# Generate invite link
curl -X POST https://skillbridge-api.onrender.com/batches/1/invite \
  -H "Authorization: Bearer $TRAINER_TOKEN"

# Join batch (student)
STUDENT_TOKEN=$(curl -s -X POST https://skillbridge-api.onrender.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"aarav@student.com","password":"Password123!"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -X POST https://skillbridge-api.onrender.com/batches/join \
  -H "Authorization: Bearer $STUDENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"token":"<invite_token_from_above>"}'

# Batch summary (institution)
INST_TOKEN=$(curl -s -X POST https://skillbridge-api.onrender.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"sunrise@inst.com","password":"Password123!"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl https://skillbridge-api.onrender.com/batches/1/summary \
  -H "Authorization: Bearer $INST_TOKEN"
```

### Sessions

```bash
# Create session (trainer)
curl -X POST https://skillbridge-api.onrender.com/sessions \
  -H "Authorization: Bearer $TRAINER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Intro to Python","date":"2025-06-01","start_time":"09:00:00","end_time":"11:00:00","batch_id":1}'

# Get attendance for a session (trainer)
curl https://skillbridge-api.onrender.com/sessions/1/attendance \
  -H "Authorization: Bearer $TRAINER_TOKEN"
```

### Attendance

```bash
# Student marks attendance
curl -X POST https://skillbridge-api.onrender.com/attendance/mark \
  -H "Authorization: Bearer $STUDENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"session_id":1,"status":"present"}'
```

### Programme Manager

```bash
PM_TOKEN=$(curl -s -X POST https://skillbridge-api.onrender.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"deepa@programme.com","password":"Password123!"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Institution summary
curl https://skillbridge-api.onrender.com/institutions/1/summary \
  -H "Authorization: Bearer $PM_TOKEN"

# Programme-wide summary
curl https://skillbridge-api.onrender.com/programme/summary \
  -H "Authorization: Bearer $PM_TOKEN"
```

### Monitoring Officer

```bash
# Step 1: get standard token
MONITOR_STD=$(curl -s -X POST https://skillbridge-api.onrender.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"vikram@monitoring.com","password":"Password123!"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Step 2: exchange for scoped monitoring token
MONITOR_SCOPED=$(curl -s -X POST https://skillbridge-api.onrender.com/auth/monitoring-token \
  -H "Authorization: Bearer $MONITOR_STD" \
  -H "Content-Type: application/json" \
  -d '{"key":"sk_monitor_2024_securekey_abc123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Step 3: use scoped token to read attendance
curl https://skillbridge-api.onrender.com/monitoring/attendance \
  -H "Authorization: Bearer $MONITOR_SCOPED"

# POST should return 405
curl -X POST https://skillbridge-api.onrender.com/monitoring/attendance
```

---

## Running Tests

```bash
# All tests (SQLite in-memory — fast, no DB needed)
pytest tests/ -v

# Real DB tests only (requires DATABASE_URL in .env)
pytest tests/ -v -k "real_db"

# Skip real DB tests
pytest tests/ -v -k "not real_db"
```

---

## Render Deployment

1. Create a new Render service and connect your GitHub/Git repo.
2. Set the service type to **Web Service** and choose **Python**.
3. In Render service settings, set the start command:
   `uvicorn src.main:app --host 0.0.0.0 --port $PORT`
4. Add required environment variables in Render:
   - `DATABASE_URL`
   - `SECRET_KEY`
   - `ALGORITHM`
   - `ACCESS_TOKEN_EXPIRE_HOURS`
   - `MONITORING_TOKEN_EXPIRE_HOURS`
   - `MONITORING_API_KEY`
5. Deploy and verify the app at `/` and `/docs`.

> If you use Render’s managed PostgreSQL, copy its connection URL into `DATABASE_URL`.

---

## JWT Payload Structure

### Standard token (all roles, 24h)
```json
{
  "sub": "42",
  "role": "trainer",
  "token_type": "standard",
  "iat": 1717200000,
  "exp": 1717286400
}
```

### Monitoring scoped token (monitoring_officer only, 1h)
```json
{
  "sub": "99",
  "role": "monitoring_officer",
  "token_type": "monitoring",
  "iat": 1717200000,
  "exp": 1717203600
}
```

---

## Schema Decisions

### `batch_trainers` (many-to-many)
Multiple trainers can co-deliver the same batch. A join table is used instead of a simple FK on `batches.trainer_id` to avoid a 1-to-1 constraint. A `UniqueConstraint(batch_id, trainer_id)` prevents duplicate assignments.

### `batch_invites`
Invite tokens are random URL-safe 32-byte strings. Each token is single-use (`used` boolean) and time-limited (`expires_at`). This lets trainers distribute join links without giving students direct batch IDs, and allows the trainer to revoke access by expiry or usage.

### Dual-token for Monitoring Officer
Standard login issues a 24h JWT. To access `/monitoring/attendance`, the officer must additionally present a valid API key to `/auth/monitoring-token`, which returns a 1h scoped token with `token_type: "monitoring"`. This means even a stolen standard token cannot access monitoring data without also knowing the API key — a second factor of protection.

---

## Token Rotation / Revocation (production approach)

In a production deployment, tokens would be revoked via a Redis allowlist or blocklist. On login, a token JTI (unique ID) is stored in Redis with a TTL matching the token's expiry. On each request, the JTI is checked against the store. To revoke a token, delete its JTI from Redis. Refresh tokens would allow silent renewal without re-login.

---

## Known Security Issue

**Current:** The `MONITORING_API_KEY` is hardcoded as a single value in `.env`. If it leaks, all monitoring access is compromised with no per-officer revocation.

**Fix with more time:** Issue per-officer API keys stored as bcrypt-hashed values in the database, with a `key_id` included in the monitoring token payload. Rotation would invalidate the old key for that officer only. An audit log would record each key exchange event.

---

## What's Working / Partial / Skipped

| Area | Status |
|---|---|
| All 14 endpoints | ✅ Fully implemented |
| RBAC on every protected endpoint | ✅ Enforced via FastAPI dependencies |
| JWT auth (standard + monitoring) | ✅ Both token types with correct expiry |
| Validation & 422/404/403/405 errors | ✅ All error cases handled |
| Seed script (2 inst, 4 trainers, 15 students, 3 batches, 8 sessions) | ✅ Working |
| 5+ pytest tests (2 hitting real DB) | ✅ 7 tests total |
| Deployment (Render/Railway) | ✅ See live URL above |
| Password hashing (bcrypt via passlib) | ✅ |
| Frontend UI | ⚠️ Not in scope per assignment — API only |
| Token refresh endpoint | ⚠️ Skipped — 24h expiry is sufficient for prototype |
| Rate limiting | ⚠️ Skipped — would add via slowapi in production |

---

## One Thing I'd Do Differently

I'd introduce **Alembic** for database migrations from day one. Using `Base.metadata.create_all()` on startup is fine for a prototype but breaks in production when you need to alter existing tables without dropping data. Alembic gives you reversible, auditable schema changes and a migration history that teammates can run.

---

## Deployment Notes

Deployed on **Render** with:
- `Start command`: `uvicorn src.main:app --host 0.0.0.0 --port $PORT`
- Environment variables set via Render dashboard (not committed to repo)
- Neon PostgreSQL connected via `DATABASE_URL`
- `seed.py` run manually once via Render shell after first deploy

No credentials are committed to the repository.
