import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Flame } from 'lucide-react'
import { api } from '../services/api'
import type { ProgressData } from '../types'

export default function Progress() {
  const [data, setData] = useState<ProgressData | null>(null)

  useEffect(() => {
    api<ProgressData>('/api/progress')
      .then(setData)
      .catch(() => {})
  }, [])

  return (
    <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
      <h1 className="text-lg font-bold text-navy-900">અભ્યાસ પ્રગતિ 📊</h1>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'પ્રશ્નો પૂછ્યા', value: data?.questions_asked ?? 0, icon: '💬' },
          { label: 'ક્વિઝ એટેમ્પ્ટ', value: data?.quiz_attempts ?? 0, icon: '🧠' },
          { label: 'પ્રકરણો', value: data?.chapters_studied ?? 0, icon: '📖' },
          { label: 'સતત દિવસ', value: data?.streak_days ?? 0, icon: '🔥' },
        ].map(({ label, value, icon }) => (
          <div key={label} className="bg-white rounded-2xl shadow-card p-4 text-center">
            <div className="text-xl">{icon}</div>
            <div className="mt-1 text-2xl font-extrabold text-navy-900">{value}</div>
            <div className="text-[11px] text-navy-400">{label}</div>
          </div>
        ))}
      </div>

      {/* Subject progress bars */}
      <section className="bg-white rounded-2xl shadow-card p-5">
        <h2 className="font-bold text-navy-900 mb-3">વિષય પ્રમાણે પ્રગતિ</h2>
        <div className="space-y-3">
          {(data?.subjects || []).map((s) => (
            <div key={s.subject_id || s.name_gu}>
              <div className="flex justify-between text-sm mb-1">
                <span className="font-medium text-navy-800">
                  {s.icon} {s.name_gu}
                </span>
                <span className="text-navy-400">{Math.round(s.avg_completion)}%</span>
              </div>
              <div className="h-2.5 rounded-full bg-navy-100 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${
                    s.avg_completion >= 80
                      ? 'bg-brand-green'
                      : s.avg_completion >= 50
                      ? 'bg-brand-blue'
                      : 'bg-brand-orange'
                  }`}
                  style={{ width: `${Math.round(s.avg_completion)}%` }}
                />
              </div>
            </div>
          ))}
          {(!data?.subjects || data.subjects.length === 0) && (
            <p className="text-sm text-navy-400 text-center py-4">
              હજી અભ્યાસ શરૂ નથી. ચેટમાં પ્રશ્ન પૂછો અથવા ક્વિઝ રમો!
            </p>
          )}
        </div>
      </section>

      {/* Chapters */}
      <section className="bg-white rounded-2xl shadow-card p-5">
        <h2 className="font-bold text-navy-900 mb-3">પ્રકરણ પ્રગતિ</h2>
        <div className="space-y-2">
          {(data?.chapters || []).slice(0, 10).map((c) => (
            <Link
              key={c.id}
              to={`/chapters/${c.id}`}
              className="flex items-center gap-3 rounded-xl px-3 py-2.5 hover:bg-navy-50 transition"
            >
              <span className="text-xl">{c.subject_icon}</span>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-navy-900 truncate">
                  {c.chapter_number}. {c.chapter_name}
                </div>
                <div className="text-[11px] text-navy-400">
                  {c.subject_name} · 💬 {c.questions_asked} પ્રશ્નો · 🧠 શ્રેષ્ઠ {Math.round(c.best_quiz_score)}%
                </div>
              </div>
              <div className="w-16 h-2 rounded-full bg-navy-100 overflow-hidden shrink-0">
                <div className="h-full bg-brand-green rounded-full" style={{ width: `${Math.round(c.completion_percent)}%` }} />
              </div>
            </Link>
          ))}
          {(!data?.chapters || data.chapters.length === 0) && (
            <p className="text-sm text-navy-400 text-center py-4">હજી કોઈ પ્રકરણ અભ્યાસેલ નથી.</p>
          )}
        </div>
      </section>

      {/* Recent quiz scores */}
      {(data?.recent_quiz?.length || 0) > 0 && (
        <section className="bg-white rounded-2xl shadow-card p-5">
          <h2 className="font-bold text-navy-900 mb-3">તાજી ક્વિઝ</h2>
          <div className="space-y-2">
            {data!.recent_quiz.map((q) => (
              <div key={q.id} className="flex items-center gap-3 text-sm">
                <div className="flex-1 text-navy-600">
                  {new Date(q.completed_at || '').toLocaleDateString('gu-IN')}
                </div>
                <div className="font-semibold text-navy-900">
                  {q.correct_count}/{q.total_questions}
                </div>
                <div
                  className={`w-12 text-right font-bold ${
                    q.score_percent >= 70 ? 'text-brand-green' : q.score_percent >= 40 ? 'text-brand-orange' : 'text-red-500'
                  }`}
                >
                  {Math.round(q.score_percent)}%
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      <div className="flex items-center gap-2 justify-center text-xs text-navy-400">
        <Flame size={13} className="text-brand-orange" />
        દરરોજ અભ્યાસ કરો અને સતત દિવસો વધારો!
      </div>
    </div>
  )
}
