# Gyan Sathi — ગુજરાતી વિદ્યાર્થીઓનો AI અભ્યાસ સાથી

**તમારો અભ્યાસ, અમારો સાથી**

Gyan Sathi is a production-ready AI tutor SaaS built specifically for **Gujarat Board (GSEB) Std. 9 & 10 students** studying in Gujarati medium. It combines a Gujarati-first AI tutor, a RAG knowledge base over GSEB-aligned content, quizzes, progress tracking, uploads, and a Free/Premium subscription system with server-verified payments.

<p align="center">
  <img src="frontend/public/assets/logo.png" width="220" alt="Gyan Sathi logo" />
</p>

---

## ✨ Features

| Area | What you get |
| --- | --- |
| 🤖 Gujarati AI Tutor | GSEB-aware chatbot that answers in natural Gujarati, with exam mode (2/3/5 marks), numerical mode (આપેલ→સૂત્ર→ગણતરી→જવાબ), explanation & practice modes |
| 📚 RAG Knowledge Base | PDF/TXT/MD/DOCX ingestion → semantic chunking → NVIDIA embeddings → **pgvector** similarity search → grounded answers with **source display** (ધોરણ/વિષય/પ્રકરણ/પાનું) |
| 🔐 Email OTP Auth | **Self-contained email OTP** — send codes straight from the backend via any SMTP provider (Brevo/Gmail/Resend). No auth vendor required; Supabase is optional. |
| 🧠 Quizzes | AI-generated MCQs from the knowledge base, one-question-at-a-time UI, scoring, explanations, attempt history |
| 📊 Student Progress | Questions asked, chapters studied, per-subject progress bars, quiz scores, streaks |
| 📁 Uploads | Files analyzed by AI; **server-side 10-upload free limit** (usage-based, never restored on delete) |
| 👑 Premium ₹10/year | DB-driven plans, Razorpay-ready payment architecture (live + sandbox), server-side signature verification |
| 🛡️ Admin Panel | Dashboard, students, subjects/chapters CRUD, knowledge ingestion & semantic search, subscriptions/payments, feedback review |
| ⚡ Performance | Redis caching (answers, RAG, rate limits) with in-memory fallback, streaming responses, code-split frontend, DB indexes, pgvector index |

---

## 🏗️ Architecture

```
┌─────────────────┐     /api proxy      ┌──────────────────────┐
│  React + Vite    │ ──────────────────► │  FastAPI (async)     │
│  TS · Tailwind   │ ◄────────────────── │  JWT auth · RBAC     │
└─────────────────┘   JSON / SSE stream  └──────────┬───────────┘
                                                    │
                     ┌──────────────────────────────┼──────────────────┐
                     ▼                 ▼            ▼                  ▼
              ┌────────────┐   ┌──────────────┐  ┌────────┐    ┌──────────────┐
              │ Supabase   │   │ PostgreSQL + │  │ Redis  │    │ NVIDIA NIM   │
              │ Auth (OTP) │   │ pgvector     │  │ cache  │    │ LLM + embed  │
              │ Storage    │   │ (Supabase)   │  │ limits │    │ (provider IF)│
              └────────────┘   └──────────────┘  └────────┘    └──────────────┘
```

**AI provider abstraction** — `AIService → AIProvider(ABC) → NVIDIAProvider` (swap to Gemini/OpenAI via `.env`, never hard-coded).

**RAG flow** — question → detect ધોરણ/વિષય/પ્રકરણ → embed query → pgvector search (metadata-filtered) → context build → Gujarati system prompt → answer + sources. Low-retrieval answers clearly tell students the info is not from the knowledge base.

**Knowledge hierarchy respected** — `gseb > textbook > question_bank > curated > demo` (`source_type`), with honesty rules against fabricated page numbers/sources.

---

## 🧰 Tech Stack

- **Frontend**: React 18 · TypeScript · Vite · Tailwind CSS · Lucide icons · react-markdown + KaTeX (math rendering)
- **Backend**: FastAPI · SQLAlchemy 2 · Pydantic v2 · JWT (PyJWT) · passlib
- **Database**: PostgreSQL (Supabase) with **pgvector**
- **Cache/limits**: Redis (optional — falls back to in-memory)
- **Auth**: Own email-OTP (direct SMTP) + app JWT; password login for admins; Supabase auth optional
- **AI**: NVIDIA NIM (OpenAI-compatible) — chat + embeddings
- **Payments**: Razorpay (live) + sandbox mode for development

---

## 🚀 Quick Start (Local Development)

### 0. Prerequisites
Python 3.11+, Node 20+, and a **Supabase project** (free tier works).

### 1. Database setup — step by step

> **Good to know:** Supabase is used here only as a **free Postgres + pgvector host**. Gyan Sathi's
> email OTP does **not** require Supabase — the backend sends OTP emails itself over SMTP (step 1.6).
> Any Postgres-with-pgvector host works (Supabase, Neon, self-hosted Docker via `docker-compose.yml`).

#### Step 1.1 — Create the project
1. Go to [supabase.com](https://supabase.com) → **New project**.
2. Pick a strong database password (you'll need it in step 1.3) and a region close to your users (e.g. Mumbai `ap-south-1`).
3. Wait for provisioning (~2 minutes).

#### Step 1.2 — Enable pgvector
In the left sidebar: **Database → Extensions** → search `vector` → **Enable**.

Or run in **SQL Editor**:
```sql
create extension if not exists vector;
```
> Supabase installs extensions into the `extensions` schema. The backend already sets
> `search_path=public,extensions` automatically, so the `vector` type resolves.

#### Step 1.3 — Copy the database URL
**Settings → Database → Connection string → Session pooler** (port `5432`). It looks like:
```
postgresql://postgres.abcdefghijklm:YOUR-PASSWORD@aws-0-ap-south-1.pooler.supabase.com:5432/postgres
```
Replace `[YOUR-PASSWORD]` with the password from step 1.1.

> Use the **Session pooler** URI for the backend. The direct connection (`db.<ref>.supabase.com:5432`)
> also works but is IPv4-restricted on free tier. Do NOT use the transaction pooler (port 6543) —
> prepared statements can conflict with it.

#### Step 1.4 — Run the schema SQL
Open **SQL Editor** → New query → paste the contents of [`supabase/schema.sql`](supabase/schema.sql) → **Run**.
This creates the pgvector index, performance indexes and the `uploads` storage bucket.
(The tables themselves are created automatically by the backend on first boot.)

#### Step 1.5 — (Optional) API credentials
**Settings → API** — only needed if you use Supabase OTP delivery or Supabase Storage. The core app (DB + own SMTP OTP) runs without these:
- **Project URL** → `SUPABASE_URL`
- **service_role key** (secret! server-only) → `SUPABASE_SERVICE_ROLE_KEY`
- **anon key** → optional, not needed by the backend
- **JWT Secret** → optional (`SUPABASE_JWT_SECRET`)

#### Step 1.6 — Email OTP WITHOUT Supabase (recommended, free)

> **You don't need Supabase for OTP at all.** Gyan Sathi sends OTP emails directly from its own
> FastAPI backend via any SMTP provider. Codes are hashed and stored with a TTL, single-use,
> with attempt limiting. This removes an entire vendor dependency.

Just fill these in `backend/.env`:

| Provider | Free tier | SMTP settings |
| --- | --- | --- |
| **Brevo** (recommended) | 300 emails/day | host `smtp-relay.brevo.com`, port 587, user/password from Brevo → SMTP & API |
| **Gmail** | ~500/day | host `smtp.gmail.com`, port 465, user = your Gmail, password = **App Password** (needs 2FA) |
| **Resend** | 100/day (+3k/month) | host `smtp.resend.com`, port 465, user `resend`, password = API key |

```ini
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USER=your-login@smtp-brevo.com
SMTP_PASSWORD=your-smtp-key
SMTP_FROM_EMAIL=hello@yourdomain.in
SMTP_FROM_NAME=Gyan Sathi
```

Restart the backend — signup OTPs now arrive from your own sender. If SMTP is left empty,
the app runs in dev mode (OTP `000000`) so development never blocks.

**(Optional) Step 1.6b — Supabase OTP instead**
If you prefer Supabase to deliver OTP emails: Project Settings → Auth → SMTP Settings (same provider
table above), then set the "Confirm signup" template body to show the code:
```html
<p style="font-size:32px;font-weight:800;letter-spacing:6px;color:#1B62B5">{{ .Token }}</p>
```
The backend automatically uses Supabase as a fallback when configured.

#### Step 1.7 — Verify everything
```bash
cd GyanSathi/backend
python -m scripts.check_supabase     # connectivity, pgvector, write access, auth config
```
All checks green → continue. If `vector type not resolvable` appears, make sure step 1.2 ran and re-check.

### 2. Backend

```bash
cd GyanSathi/backend
python -m venv .venv && .venv\Scripts\activate     # Windows (use source .venv/bin/activate on mac/linux)
pip install -r requirements.txt

copy ..\.env.example .env                           # then edit .env (see below)
python -m scripts.check_supabase                    # verify the connection first
python -m scripts.seed_database                     # plans, subjects, chapters, sample KB, admin user
uvicorn app.main:app --reload --port 8000
```

Fill these keys in `backend/.env` (from steps 1.3–1.5):
```ini
DATABASE_URL=postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOi...
```

API docs open at `http://localhost:8000/api/docs`.

### 3. Frontend

```bash
cd GyanSathi/frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` → `http://localhost:8000`.

### 4. First login

- **Admin**: `admin@gyansathi.in` / `Admin@123` (password login — change immediately)
- **Student demo**: `student@demo.in` / `Student@123`
- **New signup**: email OTP flow (`000000` works when Supabase is not configured)

---

## 🔑 Environment Variables

Copy `.env.example` → `.env` (backend) and fill:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Supabase **session pooler** URI (postgresql://…) |
| `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` | OTP + Storage (service key: **server only**) |
| `NVIDIA_API_KEY` | NVIDIA NIM key (server only, never in frontend) |
| `AI_MODEL` / `AI_MODEL_ADVANCED` / `AI_EMBEDDING_MODEL` | Configurable models (defaults verified working) |
| `JWT_SECRET` | App token signing secret |
| `RAZORPAY_KEY_ID/SECRET` | Only for live payments (`PAYMENT_MODE=live`) |
| `FREE_UPLOAD_LIMIT` / `PREMIUM_UPLOAD_LIMIT` | Upload allowances (DB plans seeded from these) |
| `REDIS_URL` | Optional; empty = in-memory cache |

> ⚠️ Never commit `.env`. The provided key in the repo history should be **rotated** before any public release.

---

## 📚 Knowledge Base Ingestion

**Admin UI (recommended)**: `/admin/knowledge` → pick ધોરણ/વિષય/પ્રકરણ + source type → upload PDF/TXT/MD/DOCX → status goes `pending → processing → completed` with chunk counts. Use the built-in **semantic search** to verify what the bot knows.

**CLI**:
```bash
python -m scripts.import_documents --dir ../knowledge-base/std10 --standard 10 --subject Science --chapter "પ્રકાશ – પરાવર્તન અને વક્રીભવન" --source-type curated
python -m scripts.generate_embeddings          # backfill missing vectors
python -m scripts.chunk_documents file.txt     # preview chunking
```

`knowledge-base/std9` and `std10` folders are provided for your own legally usable material. Only ingest content you have the rights to use.

---

## 💳 Payments

- **Development**: `PAYMENT_MODE=sandbox` — no gateway call; the verify endpoint still requires a server round-trip so the flow matches production.
- **Production (Razorpay)**:
  1. Set `PAYMENT_MODE=live` + key/secret.
  2. `/api/subscription/create` creates a Razorpay **order** (server-side).
  3. Frontend opens Razorpay Checkout with the `order_id`.
  4. `/api/subscription/verify` **verifies the HMAC signature** server-side before activating Premium.
  5. Optional: configure Razorpay webhooks → `/api/subscription/verify` style handler for reconciliation.
- Card data never touches Gyan Sathi servers. Premium is judged **only** by `subscriptions.status = active AND expires_at > now()` in the DB.

---

## 🐳 Docker

```bash
# uses local pgvector + redis (no Supabase needed)
cp .env.example .env   # fill NVIDIA_API_KEY; DATABASE_URL is overridden by compose
docker compose up --build
# frontend http://localhost:5173 · backend http://localhost:8000
docker compose exec backend python -m scripts.seed_database
```

---

## 🧪 Tests

```bash
cd GyanSathi/backend
python -m pytest tests/ -q
```

Covers: health, OTP rejection, auth guard, onboarding, admin RBAC (403 for students), quiz scoring, RAG filter detection, semantic chunking, safe filename sanitization.

---

## 📄 Project Structure

```
GyanSathi/
├── backend/
│   ├── app/
│   │   ├── api/            # auth, chat, subjects, uploads, quizzes, progress, subscriptions, admin
│   │   ├── core/           # config, security, database
│   │   ├── models/         # user, subject, chapter, knowledge, conversation, upload, subscription, quiz, progress
│   │   ├── schemas/        # pydantic request models
│   │   ├── services/       # ai_service (provider abstraction), rag, embedding, ingestion, quiz, subscription, cache, usage, supabase
│   │   ├── prompts/        # gujarati_tutor system prompt + modes
│   │   └── main.py
│   ├── scripts/            # seed, import_documents, generate_embeddings, chunk_documents
│   └── tests/
├── frontend/
│   └── src/
│       ├── components/     # Layout (sidebar + bottom nav), Logo, Markdown, LoadingScreen
│       ├── contexts/       # AuthContext
│       ├── pages/          # login, signup, onboarding, dashboard, chat, history, subjects, quiz, progress, uploads, premium, profile, settings
│       │   └── admin/      # dashboard, students, subjects, chapters, knowledge, subscriptions, analytics
│       ├── services/api.ts
│       └── types/
├── knowledge-base/         # put legally usable std9/std10 material here
├── supabase/schema.sql
├── docker-compose.yml
└── .env.example
```

---

## 🔒 Security Notes

- Secrets only in env vars; API key never reaches frontend JS.
- JWT + role-based access (`student` / `admin`); admin endpoints require `role=admin`.
- Every query scoped by `student_id` — cross-student access impossible by construction.
- Rate limiting (chat & quiz & OTP), file type/size validation, safe renamed storage, no file execution.
- Server-side upload-allowance + subscription verification (client state never trusted).
- Security headers (`X-Frame-Options`, `nosniff`, referrer policy), CORS allow-list.
- Friendly Gujarati error messages; raw errors logged server-side only.

---

## 🗺️ Roadmap (abstractions already in place)

Std 11–12 · English medium · teacher/school accounts · parent dashboard · Android/iOS (API-ready) · WhatsApp bot · voice tutor · more AI providers (drop-in `AIProvider` implementations).

---

Made with 💙 for Gujarati students. **તમારો અભ્યાસ, અમારો સાથી!**
