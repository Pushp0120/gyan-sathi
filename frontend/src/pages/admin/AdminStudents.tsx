import { useCallback, useEffect, useState } from 'react'
import { Crown, Search, UserX } from 'lucide-react'
import { api } from '../../services/api'
import type { User } from '../../types'

interface StudentRow extends User {
  is_premium: boolean
  questions_asked: number
  uploads: number
}

export default function AdminStudents() {
  const [students, setStudents] = useState<StudentRow[]>([])
  const [q, setQ] = useState('')

  const load = useCallback(() => {
    api<{ students: StudentRow[] }>(`/api/admin/students${q ? `?q=${encodeURIComponent(q)}` : ''}`)
      .then((r) => setStudents(r.students))
      .catch(() => {})
  }, [q])

  useEffect(() => {
    const t = setTimeout(load, 250)
    return () => clearTimeout(t)
  }, [load])

  const toggleActive = async (s: StudentRow) => {
    await api(`/api/admin/students/${s.id}`, {
      method: 'PATCH',
      body: JSON.stringify({ is_active: !s.is_active }),
    })
    load()
  }

  return (
    <div className="p-4 md:p-6 space-y-4">
      <h1 className="text-lg font-bold text-navy-900">વિદ્યાર્થીઓ ({students.length})</h1>

      <div className="flex items-center gap-2 rounded-xl bg-white border border-navy-100 px-3 py-2.5 max-w-md">
        <Search size={16} className="text-navy-300" />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="નામ અથવા ઈમેલથી શોધો…"
          className="flex-1 text-sm outline-none"
        />
      </div>

      <div className="bg-white rounded-2xl shadow-card overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-navy-400 border-b border-navy-100">
              <th className="px-4 py-3">વિદ્યાર્થી</th>
              <th className="px-4 py-3">ધોરણ</th>
              <th className="px-4 py-3">પ્લાન</th>
              <th className="px-4 py-3">પ્રશ્નો</th>
              <th className="px-4 py-3">અપલોડ</th>
              <th className="px-4 py-3">સ્થિતિ</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {students.map((s) => (
              <tr key={s.id} className="border-b border-navy-50 hover:bg-navy-50/40">
                <td className="px-4 py-3">
                  <div className="font-medium text-navy-900">{s.full_name || '—'}</div>
                  <div className="text-xs text-navy-400">{s.email}</div>
                </td>
                <td className="px-4 py-3">{s.standard ? `ધોરણ ${s.standard}` : '—'}</td>
                <td className="px-4 py-3">
                  {s.is_premium ? (
                    <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 text-amber-700 px-2 py-0.5 text-xs font-bold">
                      <Crown size={11} /> Premium
                    </span>
                  ) : (
                    <span className="text-xs text-navy-400">મફત</span>
                  )}
                </td>
                <td className="px-4 py-3">{s.questions_asked}</td>
                <td className="px-4 py-3">{s.uploads}</td>
                <td className="px-4 py-3">
                  {s.is_active ? (
                    <span className="text-xs text-brand-green font-semibold">સક્રિય</span>
                  ) : (
                    <span className="text-xs text-red-500 font-semibold">બંધ</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => toggleActive(s)}
                    className="p-2 rounded-lg text-red-400 hover:bg-red-50"
                    title={s.is_active ? 'ખાતું બંધ કરો' : 'ખાતું ચાલુ કરો'}
                  >
                    <UserX size={15} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {students.length === 0 && (
          <div className="text-center text-sm text-navy-400 py-8">કોઈ વિદ્યાર્થી મળ્યો નથી.</div>
        )}
      </div>
      <p className="text-[11px] text-navy-300">નોંધ: પાસવર્ડ ક્યારેય બતાવવામાં નથી આવતા.</p>
    </div>
  )
}
