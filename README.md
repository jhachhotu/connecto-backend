# Connecto Backend API Engine

Enterprise-grade, asynchronous backend powering **Connecto** — the Hyperlocal On-Demand Emergency Services Network ("Problem nearby? Help nearby.").

Built with **FastAPI**, **PostgreSQL** (optimized for **Supabase Pooler** in PgBouncer transaction mode), **OAuth2 & JWT**, **Razorpay / Stripe Escrow Payments**, and **Alembic Database Migrations**.

---

## 🏛️ Architectural Overview

This backend is architected following Clean Architecture and Domain-Driven Design (DDD) principles for mission-critical dispatch and financial settlement:

```
connecto-backend/
├── app/
│   ├── main.py                     # Application entry point, CORS, lifespan, and health check
│   ├── core/
│   │   ├── config.py               # Pydantic v2 BaseSettings, Supabase pooler auto-formatting
│   │   ├── database.py             # Async SQLAlchemy engine with pool_pre_ping & PgBouncer flags
│   │   └── security.py             # JWT token issuance, bcrypt hashing & Google OAuth2 verifier
│   ├── models/                     # SQLAlchemy 2.0 ORM domain models
│   │   ├── user.py                 # Users & Verified Technician Passport profiles
│   │   ├── category.py             # 12 Emergency Trades & Service Catalog
│   │   ├── job.py                  # ServiceJob state machine & Timeline audit log
│   │   ├── quote.py                # Transparent itemized quotes (labour, parts, diagnostic, tax)
│   │   ├── payment.py              # Payments, Escrow ledger & Instant Technician Payouts
│   │   ├── rating.py               # Multi-factor ratings (skill, punctuality, transparency)
│   │   ├── dispute.py              # Dispute arbitration & refund records
│   │   └── sos.py                  # 1-Tap Emergency SOS distress incidents
│   ├── schemas/                    # Pydantic v2 validation & response DTOs
│   │   ├── auth.py, user.py, category.py, job.py, quote.py, payment.py, rating.py, dispute.py, sos.py
│   ├── services/                   # Encapsulated Business Logic layer
│   │   ├── auth_service.py         # Registration, password authentication & Google OAuth2
│   │   ├── dispatch_service.py     # Hyperlocal Haversine proximity matching & auto-dispatch
│   │   ├── payment_service.py      # Razorpay/Stripe gateway integration & Escrow settlement
│   │   └── sos_service.py          # Emergency distress broadcast & priority dispatch
│   └── api/
│       ├── deps.py                 # FastAPI dependencies (get_db, get_current_user, RBAC roles)
│       └── v1/
│           ├── api.py              # Master v1 router
│           └── endpoints/          # Granular modular RESTful routers
│               ├── auth.py         # /api/v1/auth
│               ├── users.py        # /api/v1/users
│               ├── categories.py   # /api/v1/categories
│               ├── jobs.py         # /api/v1/jobs
│               ├── quotes.py       # /api/v1/quotes
│               ├── payments.py     # /api/v1/payments
│               ├── ratings.py      # /api/v1/ratings
│               ├── disputes.py     # /api/v1/disputes
│               └── sos.py          # /api/v1/sos
├── alembic/                        # Database schema versioning & migration scripts
│   ├── versions/
│   │   └── 0001_initial_schema.py  # Production migration matching all models
│   └── env.py
├── tests/                          # Automated Pytest suite
├── requirements.txt                # Pinned production dependencies
├── .env.example                    # Sample configuration template
├── Dockerfile                      # Production container image
└── docker-compose.yml              # Local containerized PostgreSQL and API stack
```

---

## ⚡ Tech Stack

| Component | Technology | Rationale |
|---|---|---|
| **Framework** | FastAPI (Python 3.11+) | Asynchronous ASGI speed, automatic OpenAPI/Swagger documentation, native type-hints |
| **Database** | PostgreSQL / Supabase | ACID transactions, robust JSON columns, GIS proximity support |
| **ORM** | SQLAlchemy 2.0 (Async) + asyncpg | Fully async I/O database queries, eager relationship loading (`selectinload`) |
| **Database Pooler** | Supabase PgBouncer (Port 6543) | Prepared statement cache disabled (`statement_cache_size=0`) for seamless transaction pooling |
| **Migrations** | Alembic | Reproducible declarative database schema migrations |
| **Auth** | OAuth2 + JWT (python-jose) + Google OAuth | RFC 6749 compliant Bearer token flows, bcrypt password hashing, token refreshes |
| **Payments & Escrow** | Razorpay & Stripe APIs | Real-time HMAC-SHA256 signature verification, escrow holding, and technician instant payouts |
| **Validation** | Pydantic v2 | High-performance Rust-backed data validation and serialization |

---

## 🔌 Supabase Pooler Configuration

Supabase provides two connection pooler ports:
1. **Transaction Mode (`port 6543`)** *(Recommended)*: Uses PgBouncer in transaction mode. Because PgBouncer reassigns backend connections per transaction, PostgreSQL prepared statement caches **must be disabled**.
2. **Session Mode (`port 5432`)**: Standard connection pool per session.

### Senior Engineer Optimization in `app/core/config.py` & `app/core/database.py`:
- Connecto auto-formats standard `postgres://` or `postgresql://` URLs from Supabase into `postgresql+asyncpg://`.
- When `SUPABASE_TRANSACTION_POOLER=True`, `connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0}` is applied to the async engine, eliminating the infamous *"prepared statement does not exist"* PgBouncer error.
- Includes `pool_pre_ping=True` and `pool_recycle=300` to smoothly recover stale connections across serverless cold starts.

Example Supabase connection string in `.env`:
```bash
DATABASE_URL="postgresql+asyncpg://postgres.[YOUR-PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?sslmode=require"
SYNC_DATABASE_URL="postgresql://postgres.[YOUR-PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?sslmode=require"
SUPABASE_TRANSACTION_POOLER=True
```

---

## 🔑 API Endpoints Directory (`/api/v1/*`)

Interactive Swagger UI is available at **`http://localhost:8000/docs`**.

### 1. Authentication & OAuth2 (`/api/v1/auth`)
- `POST /register`: Register a new Customer or Technician account.
- `POST /login`: Email & password login, returns JWT access and refresh tokens.
- `POST /login/oauth`: Form-encoded OAuth2 login for Swagger UI authorization.
- `POST /google`: Verifies Google OAuth2 ID Token, links or provisions user account.
- `POST /refresh`: Issues fresh access token using a long-lived refresh token.
- `GET /me`: Returns authenticated user profile, permissions, and worker metadata.

### 2. Users & Verified Passport (`/api/v1/users`)
- `PUT /me`: Update full name, phone number, address, or avatar.
- `PUT /worker/profile`: Worker toggles online availability and manages skill categories.
- `POST /worker/location`: Worker broadcasts periodic GPS latitude/longitude pings.
- `GET /workers/nearby`: Proximity-based radar querying verified available technicians.
- `GET /workers`: Admin console listing all workers with verification status.

### 3. Service Catalog (`/api/v1/categories`)
- `GET /`: Lists all 12 active emergency service trades with transparent diagnostic visit pricing.
- `GET /{category_id}`: Detailed category information and popular problem diagnostics.
- `POST /` & `PUT /{category_id}`: Admin operations to manage fees and emergency arrival estimates.

### 4. Hyperlocal Jobs & Dispatch (`/api/v1/jobs`)
- `POST /`: Customer dispatches emergency request; runs Haversine proximity matching.
- `GET /active`: Fetches currently active in-flight request for customer or worker.
- `GET /`: Lists jobs filtered by role (Customer orders, Worker assignments, Admin network view).
- `GET /{job_id}`: Comprehensive lifecycle view including timeline, quote, payment, and rating.
- `POST /{job_id}/accept`: Technician accepts open callout.
- `PUT /{job_id}/status`: Transitions job status (`EN_ROUTE`, `ARRIVED`, `DIAGNOSING`, `REPAIRING`, `COMPLETED`).
- `POST /{job_id}/cancel`: Cancellation handling with formal reason.

### 5. Transparent Itemized Quotes (`/api/v1/quotes`)
- `POST /{job_id}`: Technician uploads itemized breakdown (Diagnostic fee + Labour + Spares + Platform fee + 5% GST).
- `POST /{job_id}/review`: Customer authorizes or rejects quote before work begins.
- `GET /{job_id}`: Retrieves approved/pending quote details.

### 6. Payments, Escrow & Settlements (`/api/v1/payments`)
- `POST /create-order`: Generates Razorpay / Stripe gateway order.
- `POST /verify`: Verifies HMAC-SHA256 signature, holds in escrow, and settles to technician upon completion.
- `GET /{job_id}`: Fetches transaction breakdown and formal invoice number (`INV-XXXXXX`).
- `GET /payouts/worker`: Technician ledger history and instant payout settlements.
- `POST /webhook`: Async server-to-server gateway callback listener.

### 7. Ratings & Verified Passport (`/api/v1/ratings`)
- `POST /`: Customer rates technician (Overall, Skill, Punctuality, Transparency, Review text).
- `GET /worker/{worker_id}`: Aggregated trust scorecard for worker's digital passport.

### 8. Disputes & Resolution (`/api/v1/disputes`)
- `POST /`: Customer or worker files formal grievance; freezes escrow.
- `GET /`: Admin operations dispute review queue.
- `POST /{dispute_id}/resolve`: Admin resolves dispute with optional escrow refund.

### 9. Emergency SOS Operations (`/api/v1/sos`)
- `POST /trigger`: 1-Tap SOS distress broadcast with GPS coordinates and contact phone.
- `GET /`: Admin Live Incident Console.
- `POST /{sos_id}/acknowledge` & `POST /{sos_id}/resolve`: Incident mitigation workflow.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+ (or Docker)
- PostgreSQL database or Supabase account

### Option A: Local Python Virtual Environment

1. **Navigate to backend folder**:
   ```bash
   cd connecto-backend
   ```

2. **Create and activate virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your Supabase DATABASE_URL and SECRET_KEY
   ```

5. **Run database migrations**:
   ```bash
   alembic upgrade head
   ```

6. **Start the API server**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

### Option B: Docker Compose

```bash
cd connecto-backend
docker compose up --build -d
```
The API will be available at `http://localhost:8000` with PostgreSQL containerized on port `5432`.

---

## 🧪 Testing

Run automated tests using pytest:
```bash
pytest
```

---

## 🔒 Security Best Practices Implemented

- **Password Hashing**: Bcrypt with salted rounds.
- **JWT Cryptography**: Signed with HS256, strictly validated audience, expiration, and token types (`access` vs `refresh`).
- **Escrow Integrity**: Cryptographic HMAC-SHA256 signature verification on payment callbacks before releasing funds.
- **RBAC (Role-Based Access Control)**: Strict dependency injection guards (`get_current_active_worker`, `get_current_admin`).
- **SQL Injection Prevention**: 100% parameterized queries via SQLAlchemy 2.0 ORM.
- **CORS Protection**: Explicit origin whitelisting with credentials support.
