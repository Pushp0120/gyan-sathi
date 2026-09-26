# GyanSathi — Handover Guide (હસ્તાંતરણ માર્ગદર્શિકા)

This document explains everything the new owner needs to take over the
GyanSathi project: code, database, textbooks, and hosting.

---

## 1. What this project is

A Gujarati-medium GSEB Std 10 study platform:

- **Frontend:** React + Vite (`frontend/`) — deploy target: Vercel
- **Backend:** FastAPI (`backend/`) — deploy target: Vercel (`api/index.py`)
- **Database:** Neon Postgres (with pgvector for the AI knowledge base)
- **AI:** NVIDIA API key (chat answers + quiz question generation)

---

## 2. Textbooks (Google Drive) — IMPORTANT

The 8 official GCERT/GSEB textbook PDFs (~589 MB total) are **not stored in
this repository**. They live on **Google Drive** so the repo stays small and
portable.

### How the app uses them

1. Each PDF is uploaded to a Google Drive account and shared
   ("Anyone with the link → Viewer").
2. The file's **Drive FILE ID** is written into
   `backend/app/api/subjects.py` → `TEXTBOOK_PDFS`.
3. When a student opens a textbook, the backend returns a Drive **embed**
   link, and the reader page shows it in an iframe (Drive's own viewer,
   with page navigation and zoom).
4. A **download** link is also provided via Drive's direct-download URL.

### Setup steps for the new owner

1. Upload the 8 PDFs to your own Google Drive
   (names: `std10-mathematics.pdf`, `std10-science.pdf`,
   `std10-social-science.pdf`, `std10-gujarati.pdf`, `std10-english.pdf`,
   `std10-hindi.pdf`, `std10-sanskrit.pdf`, `std10-computer-studies.pdf`).
2. For each file: **Share → General access → "Anyone with the link" →
   Viewer**.
3. Copy each file's ID from its share link — the long string between
   `/d/` and `/view`:
   `https://drive.google.com/file/d/`**`THIS_PART`**`/view`
4. Open `backend/app/api/subjects.py`, find `TEXTBOOK_PDFS`, and replace
   each placeholder (e.g. `DRIVE_FILE_ID_mathematics`) with the real ID.
5. Commit and deploy. Done — no other changes needed.

Note: quiz generation and the AI chat do **not** read these PDFs; they use
the knowledge base text ingested into the database by the admin panel, so
they keep working independently of Drive.

---

## 3. Code repository transfer

1. New owner creates (or already has) a GitHub account.
2. Current owner: GitHub repo → Settings → Collaborators → **invite the new
   owner as Admin**, or transfer ownership via
   Settings → **Transfer ownership**.
3. New owner accepts. Vercel connection is re-linked in Section 5.

---

## 4. Database transfer (Neon)

Two options:

- **Option A (fastest):** transfer the Neon account/project. In Neon:
  Settings → transfer, or share credentials and have the new owner rotate
  the database password (Neon console → Roles → reset password), then
  update `DATABASE_URL` everywhere.
- **Option B (fresh start):** new owner creates a new Neon project, then
  creates the schema and seeds it:

  ```bash
  cd backend
  python -m scripts.seed_missing_chapters
  ```

  (Seed script is idempotent — safe to run multiple times.)

Either way, set the resulting connection string as `DATABASE_URL`.

---

## 5. Hosting transfer (Vercel)

1. New owner creates a Vercel account, then creates a new project imported
   from the GitHub repo (root directory: repo root; the `vercel.json` and
   `api/index.py` handle routing).
2. Set these **environment variables** in Vercel → Project → Settings →
   Environment Variables (values in the current owner's private notes):

   | Variable | Purpose |
   |---|---|
   | `DATABASE_URL` | Neon Postgres connection string |
   | `JWT_SECRET` | login token signing secret |
   | `NVIDIA_API_KEY` | AI chat + quiz generation |
   | `ADMIN_EMAILS` | admin panel access |
   | `BREVO_SMTP_USER` / `BREVO_SMTP_PASSWORD` | OTP & password mails |
   | `MAIL_FROM` | sender address for those mails |

3. **Turn OFF Vercel Deployment Protection** (Settings → Deployment
   Protection → Disabled) — otherwise visitors are forced to log in to
   Vercel and can't reach the site.
4. Redeploy. Vercel runs `npm run build` for the frontend and serves the
   FastAPI app from `api/index.py`.

### Third-party accounts to recreate/transfer

- Google Drive (textbook PDFs — see Section 2)
- Brevo (transactional email)
- NVIDIA build account (AI API key)
- Neon (database)

---

## 6. Post-handover checklist

- [ ] GitHub repo transferred / collaborator added
- [ ] Neon database accessible by new owner (`DATABASE_URL` rotated)
- [ ] 8 textbook PDFs uploaded to new owner's Drive, shared
      "Anyone with the link", FILE IDs pasted into `TEXTBOOK_PDFS`
- [ ] Vercel project re-linked to the repo, env vars set
- [ ] **Vercel Deployment Protection turned OFF**
- [ ] Site tested logged-out: login, subjects, textbook reader, quiz
- [ ] Payment mode confirmed (`upi_qr` vs `free` in `PAYMENT_MODE`)
- [ ] Brevo SMTP tested (OTP mail arrives)
- [ ] Old owner's keys revoked (NVIDIA key regenerated, Brevo password
      changed, DATABASE_URL rotated)

---

## 7. Local development (for reference)

```bash
# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env      # then fill in real values
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev               # http://localhost:5173 (proxies /api to :8000)
```

Demo logins (local/dev): `student@demo.in / Student@123`,
`admin@gyansathi.in / Admin@123`.
