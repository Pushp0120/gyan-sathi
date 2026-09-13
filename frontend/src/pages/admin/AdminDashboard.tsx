import { useEffect, useState } from 'react'
import { api } from '../../services/api'

interface Dash {
  total_students: number
  active_students: number
  premium_students: number
  free_students: number
  total_questions: number
  total_uploads: number
  total_tokens: number
  revenue_inr: number
  popular_subjects: { name: string; count: number }[]
  recent_activity: { when: string; student: string; type: string; preview: string }[]
}

export default function AdminDashboard() {
  const [d, setD] = useState<Dash | null>(null)

  useEffect(() => {
    api<Dash>('/api/admin/dashboard')
      .then(setD)
      .catch(() => {})
  }, [])

  const cards = [
    { label: 'કુલ વિદ્યાર્થીઓ', value: d?.total_students, icon: '🎓', color: 'bg-brand-blue' },
    { label: 'સક્રિય', value: d?.active_students, icon: '✅', color: 'bg-brand-green' },
    { label: 'Premium', value: d?.premium_students, icon: '👑', color: 'bg-brand-orange' },
    { label: 'મફત', value: d?.free_students, icon: '🆓', color: 'bg-slate-400' },
    { label: 'કુલ પ્રશ્નો', value: d?.total_questions, icon: '💬', color: 'bg-purple-500' },
    { label: 'અપલોડ', value: d?.total_uploads, icon: '📁', color: 'bg-sky-500' },
    { label: 'AI ટોકન', value: d?.total_tokens?.toLocaleString(), icon: '🤖', color: 'bg-navy-700' },
    { label: 'આવક (₹)', value: d?.revenue_inr, icon: '💰', color: 'bg-emerald-600' },
  ]

  return (
    <div className="p-4 md:p-6 space-y-6">
      <h1 className="text-lg font-bold text-navy-900">એડમિન ડેશબોર્ડ</h1>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {cards.map((c) => (
          <div key={c.label} className="bg-white rounded-2xl shadow-card p-4">
            <div className={`inline-flex p-2 rounded-xl ${c.color} text-white text-lg`}>{c.icon}</div>
            <div className="mt-2 text-2xl font-extrabold text-navy-900">{c.value ?? '—'}</div>
            <div className="text-xs text-navy-400">{c.label}</div>
          </div>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <div className="bg-white rounded-2xl shadow-card p-5">
          <h2 className="font-bold text-navy-900 mb-3">લોકપ્રિય વિષયો</h2>
          <div className="space-y-2">
            {(d?.popular_subjects || []).map((s) => (
              <div key={s.name} className="flex items-center gap-2 text-sm">
                <span className="flex-1 text-navy-700">{s.name}</span>
                <div className="w-32 h-2 rounded-full bg-navy-100 overflow-hidden">
                  <div
                    className="h-full bg-brand-orange rounded-full"
                    style={{
                      width: `${Math.min(100, (s.count / Math.max(1, d!.popular_subjects[0].count)) * 100)}%`,
                    }}
                  />
                </div>
                <span className="text-xs text-navy-400 w-8 text-right">{s.count}</span>
              </div>
            ))}
            {(!d?.popular_subjects?.length && (
              <p className="text-sm text-navy-400">હજી ડેટા નથી.</p>
            )) || null}
          </div>
        </div>

        <div className="bg-white rounded-2xl shadow-card p-5">
          <h2 className="font-bold text-navy-900 mb-3">તાજી પ્રવૃત્તિ</h2>
          <div className="space-y-2 max-h-72 overflow-y-auto">
            {(d?.recent_activity || []).map((a, i) => (
              <div key={i} className="text-xs border-b border-navy-50 pb-2">
                <div className="flex justify-between">
                  <span className="font-semibold text-navy-800">{a.student}</span>
                  <span className="text-navy-300">
                    {a.when ? new Date(a.when).toLocaleTimeString('gu-IN', { hour: '2-digit', minute: '2-digit' }) : ''}
                  </span>
                </div>
                <div className="text-navy-500 truncate">{a.preview}</div>
              </div>
            ))}
            {!d?.recent_activity?.length && <p className="text-sm text-navy-400">હજી પ્રવૃત્તિ નથી.</p>}
          </div>
        </div>
      </div>
    </div>
  )
}
