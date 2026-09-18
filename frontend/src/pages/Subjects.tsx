import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { BookOpen, ListChecks } from 'lucide-react'
import { api } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import type { Subject } from '../types'

export default function Subjects() {
  const { user } = useAuth()
  const [subjects, setSubjects] = useState<Subject[]>([])

  useEffect(() => {
    if (user?.standard) {
      api<{ subjects: Subject[] }>(`/api/subjects?standard=${user.standard}`)
        .then((r) => setSubjects(r.subjects))
        .catch(() => {})
    }
  }, [user?.standard])

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      <h1 className="text-lg font-bold text-navy-900">ધોરણ {user?.standard} — વિષયો</h1>
      <p className="text-sm text-navy-500 mt-1 mb-5">
        વિષય પર ક્લિક કરો અને સંપૂર્ણ અધિકૃત પાઠ્યપુસ્તક વાંચો
      </p>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {subjects.map((s) => (
          <div
            key={s.id}
            className="bg-white rounded-2xl shadow-card overflow-hidden hover:shadow-card-hover hover:-translate-y-0.5 transition flex flex-col"
          >
            <Link to={`/textbook/${s.id}`} className="p-5 pb-3 flex-1">
              <div className="text-3xl">{s.icon}</div>
              <div className="mt-2 font-bold text-navy-900">{s.name_gu}</div>
              <div className="text-xs text-navy-400 flex items-center gap-1 mt-1">
                <BookOpen size={12} /> સંપૂર્ણ પાઠ્યપુસ્તક (PDF)
              </div>
            </Link>
            <Link
              to={`/subjects/${s.id}`}
              className="flex items-center gap-1.5 px-5 py-2 text-[11px] font-semibold text-navy-500 bg-slate-50 border-t border-navy-100/70 hover:text-brand-blue hover:bg-slate-100 transition"
            >
              <ListChecks size={12} /> પ્રકરણ-વાર અભ્યાસ
            </Link>
          </div>
        ))}
      </div>
    </div>
  )
}
