-- Gyan Sathi — Supabase schema helpers
-- Run this in the Supabase SQL Editor once, before starting the backend.
-- (Tables themselves are created automatically by the backend via SQLAlchemy.)

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

-- 4) Storage bucket for uploads (public-read for simple display; tighten if needed)
insert into storage.buckets (id, name, public) values ('uploads', 'uploads', true)
on conflict (id) do nothing;
