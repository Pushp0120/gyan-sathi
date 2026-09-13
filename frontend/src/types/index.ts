export interface User {
  id: string
  email: string
  full_name: string
  role: 'student' | 'admin' | 'teacher'
  standard: number | null
  medium: string
  preferred_language: string
  onboarded: boolean
  streak_days: number
  is_active: boolean
  created_at: string | null
}

export interface Subject {
  id: string
  standard: number
  name_en: string
  name_gu: string
  code: string
  icon: string
  color: string
  sort_order: number
  is_active: boolean
}

export interface Chapter {
  id: string
  subject_id: string
  number: number
  name_en: string
  name_gu: string
  description: string
  is_active: boolean
}

export interface RagSource {
  index: number
  standard: number | null
  subject_gu: string | null
  chapter_gu: string | null
  chapter_number: number | null
  page_number: number | null
  section: string | null
  source: string | null
  academic_year: string | null
  source_type: string | null
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  mode: string
  sources: RagSource[]
  used_rag: boolean
  feedback: 'up' | 'down' | null
  created_at: string | null
  pending?: boolean
}

export interface Conversation {
  id: string
  title: string
  standard: number | null
  subject_id: string | null
  chapter_id: string | null
  created_at: string | null
  updated_at: string | null
}

export interface QuizQuestion {
  id?: string
  question: string
  options: string[]
  answer: string
  explanation: string
  difficulty: string
}

export interface UploadAllowance {
  used: number
  limit: number
  remaining: number | null
  can_upload: boolean
  is_premium: boolean
}

export interface UploadItem {
  id: string
  original_name: string
  mime_type: string
  file_size: number
  file_type: string
  storage_url: string
  analysis_status: string
  created_at: string | null
}

export interface Plan {
  id: string
  code: string
  name_en: string
  name_gu: string
  price_inr: number
  duration_days: number
  upload_limit: number
  chat_daily_limit: number
  features: string[]
}

export interface SubscriptionStatus {
  is_premium: boolean
  subscription: {
    id: string
    status: string
    expires_at: string | null
    plan: Plan | null
  } | null
  usage: {
    daily: { ai_requests: number; uploads: number; quiz_generations: number; tokens_used: number }
    monthly: { ai_requests: number; tokens_used: number }
    upload: UploadAllowance
  }
  payment_mode: string
}

export interface ProgressData {
  questions_asked: number
  quiz_attempts: number
  chapters_studied: number
  streak_days: number
  recent_quiz: {
    id: string
    score_percent: number
    correct_count: number
    total_questions: number
    completed_at: string | null
  }[]
  subjects: { subject_id: string | null; name_gu: string; icon: string; chapters: number; avg_completion: number }[]
  chapters: {
    id: string
    chapter_name: string
    chapter_number: number
    subject_name: string
    subject_icon: string
    questions_asked: number
    quiz_attempts: number
    best_quiz_score: number
    completion_percent: number
    last_studied_at: string | null
  }[]
}
