-- Gyan Sathi — Postgres schema helpers
-- Works on ANY Postgres with pgvector: Supabase, Neon, RDS, local Docker.
-- Run this once, before starting the backend.
-- (Tables themselves are created automatically by the backend via SQLAlchemy.)
--
-- ⚠ SECTION 4 is Supabase-only (storage.buckets system schema).
--   On Neon / RDS / local Postgres: run sections 1–3, SKIP section 4.

-- 1) Enable pgvector
create extension if not exists vector;

-- 2) Vector column is created by SQLAlchemy as vector(2048) via the pgvector lib.
--    Add the ANN index for cosine distance search.
--    (Safe to run after the first backend boot, when knowledge_chunks exists.)
do $$
begin
  if exists (select 1 from information_schema.tables
             where table_schema = 'public' and table_name = 'knowledge_chunks') then
    execute 'create index if not exists ix_kc_embedding on knowledge_chunks
             using ivfflat (embedding vector_cosine_ops) with (lists = 100)';
  end if;
end $$;

-- 3) Extra performance indexes (idempotent)
create index if not exists ix_users_email on users (email);
create index if not exists ix_users_standard on users (standard);
create index if not exists ix_chapters_subject on chapters (subject_id);
create index if not exists ix_conversations_student on conversations (student_id);
create index if not exists ix_messages_conversation on messages (conversation_id);
create index if not exists ix_uploads_student on uploads (student_id);
create index if not exists ix_subscriptions_student on subscriptions (student_id);
create index if not exists ix_subscriptions_status on subscriptions (status);

-- 4) Storage bucket for uploads — SUPABASE ONLY (Supabase's storage.buckets
--    system schema does not exist on Neon/RDS/local Postgres — skip it there).
--    On Neon, uploads are stored on the server filesystem (/tmp on Vercel).
insert into storage.buckets (id, name, public) values ('uploads', 'uploads', true)
on conflict (id) do nothing;
