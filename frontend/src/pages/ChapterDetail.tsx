import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { BookOpenCheck, Brain, FileQuestion, ListChecks, Sparkles } from 'lucide-react'
import { api } from '../services/api'
import type { Chapter, Subject } from '../types'

export default function ChapterDetail() {
  const { chapterId } = useParams()
  const navigate = useNavigate()
  const [chapter, setChapter] = useState<Chapter | null>(null)
  const [subject, setSubject] = useState<Subject | null>(null)

  useEffect(() => {
    if (chapterId) {
      // Find parent subject list to resolve names
      api<{ subject: Subject; chapters: Chapter[] }>(`/api/subjects`)
        .then(() => {})
        .catch(() => {})
    }
  }, [chapterId])

  useEffect(() => {
    const stored = sessionStorage.getItem(`chapter-${chapterId}`)
    if (stored) {
      const data = JSON.parse(stored)
      setChapter(data.chapter)
      setSubject(data.subject)
    }
  }, [chapterId])

  const actions = [
    { label: 'પ્રકરણનો સાર', mode: 'summary', icon: BookOpenCheck, color: 'bg-emerald-600' },
    { label: 'મહત્વના પ્રશ્નો', mode: 'important', icon: FileQuestion, color: 'bg-purple-600' },
    { label: 'પરીક્ષા જવાબ', mode: 'exam', icon: ListChecks, color: 'bg-brand-blue' },
    { label: 'સરળ સમજૂતી', mode: 'explain', icon: Sparkles, color: 'bg-brand-orange' },
  ]

  const startChat = (mode: string, q?: string) => {
    sessionStorage.setItem(
      'chat-context',
      JSON.stringify({ subjectId: subject?.id, chapterId, mode })
    )
    navigate(q ? `/chat?mode=${mode}&q=${encodeURIComponent(q)}` : `/chat?mode=${mode}`)
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-6">
      <div className="bg-gradient-to-br from-navy-900 to-brand-blue rounded-2xl p-5 text-white mb-5">
        <div className="text-xs text-white/70">{subject?.name_gu} · ધોરણ {subject?.standard}</div>
        <h1 className="text-xl font-extrabold mt-1">
          પ્રકરણ {chapter?.number}: {chapter?.name_gu}
        </h1>
        {chapter?.name_en && <div className="text-xs text-white/60 mt-0.5">{chapter.name_en}</div>}
      </div>

      <div className="grid grid-cols-2 gap-3 mb-6">
        {actions.map(({ label, mode, icon: Icon, color }) => (
          <button
            key={mode}
            onClick={() => startChat(mode)}
            className="flex items-center gap-3 bg-white rounded-2xl shadow-card p-4 hover:shadow-card-hover transition text-left"
          >
            <span className={`p-2 rounded-xl ${color} text-white`}>
              <Icon size={18} />
            </span>
            <span className="text-sm font-semibold text-navy-900">{label}</span>
          </button>
        ))}
      </div>

      <div className="bg-white rounded-2xl shadow-card p-5">
        <h2 className="font-bold text-navy-900 mb-2">આ પ્રકરણ વિશે પૂછો</h2>
        <div className="flex gap-2">
          <input
            id="chapter-q"
            placeholder="દા.ત. આ પ્રકરણ સરળ ભાષામાં સમજાવો"
            className="flex-1 rounded-xl border border-navy-100 px-3 py-2.5 text-sm outline-none focus:border-brand-blue"
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                const q = (e.target as HTMLInputElement).value
                if (q.trim()) startChat('ask', q.trim())
              }
            }}
          />
          <button
            onClick={() => {
              const el = document.getElementById('chapter-q') as HTMLInputElement
              if (el.value.trim()) startChat('ask', el.value.trim())
            }}
            className="rounded-xl bg-brand-blue text-white px-4 text-sm font-semibold"
          >
            પૂછો
          </button>
        </div>
      </div>

      <Link
        to="/quiz"
        className="mt-4 flex items-center gap-3 bg-amber-50 border border-amber-200 rounded-2xl p-4 hover:bg-amber-100 transition"
      >
        <Brain className="text-brand-orange" size={22} />
        <div className="flex-1">
          <div className="text-sm font-bold text-navy-900">આ પ્રકરણની ક્વિઝ રમો</div>
          <div className="text-xs text-navy-500">AI તમારા પ્રકરણ પરથી પ્રશ્નો બનાવશે</div>
        </div>
      </Link>
    </div>
  )
}
