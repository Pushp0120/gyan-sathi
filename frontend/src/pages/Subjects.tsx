import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
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
      <p className="text-sm text-navy-500 mt-1 mb-5">વિષય પસંદ કરો અને પ્રકરણ પ્રમાણે અભ્યાસ કરો</p>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {subjects.map((s) => (
          <Link
            key={s.id}
            to={`/subjects/${s.id}`}
            className="bg-white rounded-2xl shadow-card p-5 hover:shadow-card-hover hover:-translate-y-0.5 transition"
          >
            <div className="text-3xl">{s.icon}</div>
            <div className="mt-2 font-bold text-navy-900">{s.name_gu}</div>
            <div className="text-xs text-navy-400">{s.name_en}</div>
          </Link>
        ))}
      </div>
    </div>
  )
}
