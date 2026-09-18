import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { BookOpenCheck, Brain, Crown, FileQuestion, ListChecks, Sparkles } from 'lucide-react'
import { api } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import type { ProgressData, Subject } from '../types'
import Logo from '../components/Logo'

export default function Dashboard() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [progress, setProgress] = useState<ProgressData | null>(null)

  useEffect(() => {
    if (user?.standard) {
      api<{ subjects: Subject[] }>(`/api/subjects?standard=${user.standard}`)
        .then((r) => setSubjects(r.subjects))
        .catch(() => {})
    }
    api<ProgressData>('/api/progress')
      .then(setProgress)
      .catch(() => {})
  }, [user?.standard])

  const quickActions = [
    { to: '/chat', label: 'Gyan Sathi ને પૂછો', icon: Sparkles, color: 'bg-brand-blue' },
    { to: '/quiz', label: 'ક્વિઝ', icon: Brain, color: 'bg-brand-orange' },
    { to: '/chat?mode=summary', label: 'પ્રકરણ સાર', icon: BookOpenCheck, color: 'bg-emerald-600' },
    { to: '/chat?mode=important', label: 'મહત્વના પ્રશ્નો', icon: FileQuestion, color: 'bg-purple-600' },
  ]

  return (
    <div className="max-w-5xl mx-auto px-4 py-6 space-y-6">
      {/* Welcome */}
      <section className="bg-gradient-to-br from-navy-900 via-navy-800 to-brand-blue rounded-2xl p-6 text-white shadow-card">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h1 className="text-xl md:text-2xl font-extrabold">
              નમસ્તે, {user?.full_name || 'વિદ્યાર્થી'}! 👋
            </h1>
            <p className="text-white/80 text-sm mt-1">
              તમારો અભ્યાસ — ધોરણ {user?.standard} | 🔥 સતત {progress?.streak_days || 0} દિવસ
            </p>
          </div>
          <div className="hidden sm:block bg-white/10 rounded-xl p-2">
            <Logo size={52} withText={false} />
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {quickActions.map(({ to, label, icon: Icon, color }) => (
            <button
              key={label}
              onClick={() => navigate(to)}
              className="flex items-center gap-2 rounded-xl bg-white/10 backdrop-blur px-3.5 py-2 text-sm font-medium hover:bg-white/20 transition"
            >
              <span className={`p-1.5 rounded-lg ${color}`}>
                <Icon size={15} />
              </span>
              {label}
            </button>
          ))}
        </div>
      </section>

      {/* Continue learning */}
      {progress?.chapters && progress.chapters.length > 0 && (
        <section>
          <h2 className="font-bold text-navy-900 mb-3">ચાલુ રાખો 📚</h2>
          <div className="grid sm:grid-cols-2 gap-3">
            {progress.chapters.slice(0, 2).map((ch) => (
              <Link
                key={ch.id}
                to={`/chapters/${ch.id}`}
                className="bg-white rounded-2xl shadow-card p-4 hover:shadow-card-hover transition"
              >
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{ch.subject_icon}</span>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-semibold text-navy-900 truncate">
                      {ch.subject_name} — પ્રકરણ {ch.chapter_number}
                    </div>
                    <div className="text-xs text-navy-500 truncate">{ch.chapter_name}</div>
                  </div>
                </div>
                <div className="mt-3 h-2 rounded-full bg-navy-100 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-brand-green transition-all"
                    style={{ width: `${Math.round(ch.completion_percent)}%` }}
                  />
                </div>
                <div className="mt-1 text-xs text-navy-400">{Math.round(ch.completion_percent)}% પૂર્ણ</div>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Subjects */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-bold text-navy-900">તમારા વિષયો</h2>
          <Link to="/subjects" className="text-xs text-brand-blue font-semibold">
            બધું જુઓ →
          </Link>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {subjects.map((s) => (
            <Link
              key={s.id}
              to={`/textbook/${s.id}`}
              className="bg-white rounded-2xl shadow-card p-4 text-center hover:shadow-card-hover hover:-translate-y-0.5 transition"
            >
              <div className="text-3xl">{s.icon}</div>
              <div className="mt-2 text-sm font-semibold text-navy-900">{s.name_gu}</div>
              <div className="text-[11px] text-navy-400">{s.name_en}</div>
            </Link>
          ))}
          {subjects.length === 0 && (
            <div className="col-span-full text-sm text-navy-400 bg-white rounded-2xl p-6 text-center shadow-card">
              વિષયો લોડ થઈ રહ્યા છે…
            </div>
          )}
        </div>
      </section>

      {/* Study progress */}
      <section className="grid grid-cols-3 gap-3">
        {[
          { label: 'પ્રશ્નો પૂછ્યા', value: progress?.questions_asked ?? 0, icon: '💬' },
          { label: 'ક્વિઝ એટેમ્પ્ટ', value: progress?.quiz_attempts ?? 0, icon: '🧠' },
          { label: 'પ્રકરણો અભ્યાસ', value: progress?.chapters_studied ?? 0, icon: '📖' },
        ].map(({ label, value, icon }) => (
          <div key={label} className="bg-white rounded-2xl shadow-card p-4 text-center">
            <div className="text-xl">{icon}</div>
            <div className="mt-1 text-2xl font-extrabold text-navy-900">{value}</div>
            <div className="text-[11px] text-navy-400">{label}</div>
          </div>
        ))}
      </section>

      {!user?.email.includes('premium') && (
        <Link
          to="/premium"
          className="flex items-center gap-3 bg-gradient-to-r from-brand-orange to-amber-400 rounded-2xl p-4 text-white shadow-card hover:shadow-card-hover transition"
        >
          <Crown size={26} />
          <div className="flex-1">
            <div className="font-bold text-sm">Gyan Sathi Premium — ₹10/વર્ષ</div>
            <div className="text-xs text-white/85">500 uploads, પ્રાધાન્યતા એક્સેસ અને વધુ</div>
          </div>
          <ListChecks size={18} />
        </Link>
      )}
    </div>
  )
}
