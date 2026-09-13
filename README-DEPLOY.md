# Gyan Sathi — Deploy to GitHub + Vercel

This project deploys to **Vercel as a single project**: the React frontend is served
as a static site, and the FastAPI backend runs as a Python serverless function
handling every `/api/*` route.

```
Browser → https://your-app.vercel.app
            ├── /            → React app (static, frontend/dist)
            └── /api/*       → FastAPI (serverless, backend/app/main.py)
```

---

## Step 1 — External services (create BEFORE importing to Vercel)

Vercel is stateless — the database, cache, file storage and email must be cloud services:

| Need | Recommended free service | What you get |
| --- | --- | --- |
| PostgreSQL + pgvector | **Supabase** or **Neon** | Free tier is enough to start |
| Redis (optional) | **Upstash** | Free 10k commands/day. Skip it — the app falls back to in-memory cache per serverless instance (works, less cache reuse) |
| OTP emails | **Brevo** SMTP | 300 free emails/day |
| AI | **NVIDIA NIM** | Your existing key |

### 1a. Database (Supabase example)
1. Create a project → enable `vector` extension (Database → Extensions).
2. SQL Editor → run the contents of `supabase/schema.sql`.
3. Copy **Settings → Database → Connection string → Session pooler** URI:
   `postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres`
   > For serverless (Vercel) prefer the **transaction pooler** URI (port 6543) if you hit
   > connection limits — SQLAlchemy works with it via `?prepared_statement_cache_size=0`.
   > Start with the session pooler; switch if you see "too many connections".

### 1b. OTP email (Brevo)
1. Create a free account at brevo.com → **SMTP & API** → copy SMTP host/port/user/password.
2. Sender: verify your email or domain.

### 1c. Seed the database (one-time, from your machine)
```bash
cd backend
# put the Supabase DATABASE_URL into backend/.env first
python -m scripts.seed_database
```

---

## Step 2 — Push to GitHub

```bash
cd GyanSathi
git init
git add .
git commit -m "Gyan Sathi — Gujarati AI tutor SaaS (FastAPI + React + pgvector RAG)"
gh repo create gyan-sathi --public --source=. --push
# or with plain git:
#   create repo 'gyan-sathi' on github.com, then:
#   git remote add origin https://github.com/<you>/gyan-sathi.git
#   git push -u origin main
```

> `.gitignore` already excludes `.env`, `*.db`, `uploads/`, `node_modules/`, `dist/`.
> Double-check with `git status` that no secret files are staged before pushing.

---

## Step 3 — Import into Vercel

1. [vercel.com](https://vercel.com) → **Add New → Project** → import `gyan-sathi`.
2. Framework Preset: **Vite** (auto-detected from `vercel.json`).
3. **Environment Variables** (Project → Settings → Environment Variables) — add:

   | Key | Value | Notes |
   | --- | --- | --- |
   | `DATABASE_URL` | your Supabase pooler URI | required |
   | `NVIDIA_API_KEY` | `nvapi-...` | required |
   | `JWT_SECRET` | long random string | required (`python -c "import secrets;print(secrets.token_hex(32))"`) |
   | `SUPABASE_URL` | `https://<ref>.supabase.co` | optional (Supabase OTP fallback) |
   | `SUPABASE_SERVICE_ROLE_KEY` | `eyJ...` | optional |
   | `SMTP_HOST` | `smtp-relay.brevo.com` | for real OTP emails |
   | `SMTP_PORT` | `587` | |
   | `SMTP_USER` / `SMTP_PASSWORD` | from Brevo | |
   | `SMTP_FROM_EMAIL` | verified sender | |
   | `SMTP_FROM_NAME` | `Gyan Sathi` | |
   | `ADMIN_EMAILS` | `admin@gyansathi.in` | seed admin |
   | `CORS_ORIGINS` | `https://your-app.vercel.app` | add custom domain later |
   | `FRONTEND_URL` | `https://your-app.vercel.app` | |
   | `ENVIRONMENT` | `production` | disables dev OTP fallback |
   | `PAYMENT_MODE` | `sandbox` | switch to `live` with Razorpay keys |
   | `AI_MODEL` / `AI_MODEL_ADVANCED` / `AI_EMBEDDING_MODEL` | defaults already in code | optional overrides |

4. **Deploy**. First build takes a few minutes (installs Python + Node deps).

---

## Step 4 — Verify

```bash
curl https://your-app.vercel.app/api/health
# {"status":"ok","app":"Gyan Sathi",...}
```

Open the app → sign up → OTP should arrive from Brevo → onboard → ask
"પ્રકાશનું પરાવર્તન સમજાવો." in the chat with વિજ્ઞાન/પ્રકાશ selected.

Admin panel: `https://your-app.vercel.app/admin` (login with the seeded admin
`ADMIN_EMAILS` / `Admin@123` — **change this password immediately**).

---

## Notes & limits

- **Serverless = stateless**: uploads go to `/tmp` (ephemeral). For durable student
  file storage, configure Supabase Storage (already supported — set `SUPABASE_URL`
  + `SUPABASE_SERVICE_ROLE_KEY` and files go to the `uploads` bucket).
- **Cold starts**: the first AI request after inactivity may take a few seconds.
- **maxDuration 60s**: quiz generation + chat fits comfortably; NVIDIA 503s are
  retried automatically.
- **Custom domain**: Vercel → Settings → Domains → add, then update
  `CORS_ORIGINS` / `FRONTEND_URL` to the new URL and re-deploy.
- **Knowledge ingestion after deploy**: run locally against the cloud DB —
  `python -m scripts.import_documents --dir ../knowledge-base/std10 --standard 10 --subject Science`
  (same `DATABASE_URL` as Vercel).
