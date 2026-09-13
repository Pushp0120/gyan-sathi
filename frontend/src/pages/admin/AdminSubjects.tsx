import { useEffect, useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import { api } from '../../services/api'
import type { Subject } from '../../types'

export default function AdminSubjects() {
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [form, setForm] = useState({ standard: 10, name_en: '', name_gu: '', icon: '📘' })
  const [showForm, setShowForm] = useState(false)

  const load = () =>
    api<{ subjects: Subject[] }>('/api/subjects')
      .then((r) => setSubjects(r.subjects))
      .catch(() => {})

  useEffect(() => {
    load()
  }, [])

  const create = async () => {
    if (!form.name_en || !form.name_gu) return
    await api('/api/admin/subjects', { method: 'POST', body: JSON.stringify(form) })
    setForm({ standard: 10, name_en: '', name_gu: '', icon: '📘' })
    setShowForm(false)
    load()
  }

  const remove = async (id: string) => {
    if (!confirm('આ વિષય બંધ કરવો છે?')) return
    await api(`/api/admin/subjects/${id}`, { method: 'DELETE' })
    load()
  }

  return (
    <div className="p-4 md:p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold text-navy-900">વિષયો</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-1 rounded-xl bg-brand-blue text-white px-3 py-2 text-xs font-semibold"
        >
          <Plus size={14} /> નવો વિષય
        </button>
      </div>

      {showForm && (
        <div className="bg-white rounded-2xl shadow-card p-4 grid grid-cols-2 md:grid-cols-5 gap-3 items-end">
          <div>
            <label className="text-xs text-navy-500">ધોરણ</label>
            <select
              value={form.standard}
              onChange={(e) => setForm({ ...form, standard: +e.target.value })}
              className="mt-1 w-full rounded-lg border border-navy-100 px-2 py-2 text-sm bg-white"
            >
              <option value={9}>ધોરણ 9</option>
              <option value={10}>ધોરણ 10</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-navy-500">Name (EN)</label>
            <input
              value={form.name_en}
              onChange={(e) => setForm({ ...form, name_en: e.target.value })}
              className="mt-1 w-full rounded-lg border border-navy-100 px-2 py-2 text-sm"
              placeholder="Science"
            />
          </div>
          <div>
            <label className="text-xs text-navy-500">નામ (ગુજરાતી)</label>
            <input
              value={form.name_gu}
              onChange={(e) => setForm({ ...form, name_gu: e.target.value })}
              className="mt-1 w-full rounded-lg border border-navy-100 px-2 py-2 text-sm"
              placeholder="વિજ્ઞાન"
            />
          </div>
          <div>
            <label className="text-xs text-navy-500">આઇકન</label>
            <input
              value={form.icon}
              onChange={(e) => setForm({ ...form, icon: e.target.value })}
              className="mt-1 w-full rounded-lg border border-navy-100 px-2 py-2 text-sm"
            />
          </div>
          <button onClick={create} className="rounded-lg bg-brand-green text-white py-2 text-sm font-semibold">
            ઉમેરો
          </button>
        </div>
      )}

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
        {subjects.map((s) => (
          <div key={s.id} className="bg-white rounded-2xl shadow-card p-4 flex items-center gap-3">
            <span className="text-2xl">{s.icon}</span>
            <div className="flex-1">
              <div className="text-sm font-bold text-navy-900">{s.name_gu}</div>
              <div className="text-xs text-navy-400">
                ધોરણ {s.standard} · {s.name_en}
              </div>
            </div>
            <button onClick={() => remove(s.id)} className="p-2 rounded-lg text-red-400 hover:bg-red-50">
              <Trash2 size={15} />
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
