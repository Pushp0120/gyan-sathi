import { useEffect, useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import { api } from '../../services/api'
import type { Chapter, Subject } from '../../types'

export default function AdminChapters() {
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [selected, setSelected] = useState('')
  const [chapters, setChapters] = useState<Chapter[]>([])
  const [form, setForm] = useState({ number: 1, name_gu: '', name_en: '' })
  const [showForm, setShowForm] = useState(false)

  useEffect(() => {
    api<{ subjects: Subject[] }>('/api/subjects')
      .then((r) => setSubjects(r.subjects))
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (!selected) return setChapters([])
    api<{ chapters: Chapter[] }>(`/api/subjects/${selected}/chapters`)
      .then((r) => setChapters(r.chapters))
      .catch(() => {})
  }, [selected])

  const create = async () => {
    if (!selected || !form.name_gu) return
    await api('/api/admin/chapters', {
      method: 'POST',
      body: JSON.stringify({ subject_id: selected, ...form, number: +form.number }),
    })
    setForm({ number: chapters.length + 1, name_gu: '', name_en: '' })
    setShowForm(false)
    const r = await api<{ chapters: Chapter[] }>(`/api/subjects/${selected}/chapters`)
    setChapters(r.chapters)
  }

  const remove = async (id: string) => {
    if (!confirm('પ્રકરણ બંધ કરવું છે?')) return
    await api(`/api/admin/chapters/${id}`, { method: 'DELETE' })
    setChapters((c) => c.filter((x) => x.id !== id))
  }

  const subject = subjects.find((s) => s.id === selected)

  return (
    <div className="p-4 md:p-6 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-lg font-bold text-navy-900">પ્રકરણો</h1>
        <div className="flex gap-2">
          <select
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
            className="rounded-xl border border-navy-100 px-3 py-2 text-sm bg-white"
          >
            <option value="">— વિષય પસંદ કરો —</option>
            {subjects.map((s) => (
              <option key={s.id} value={s.id}>
                ધોરણ {s.standard} · {s.icon} {s.name_gu}
              </option>
            ))}
          </select>
          {selected && (
            <button
              onClick={() => setShowForm(!showForm)}
              className="flex items-center gap-1 rounded-xl bg-brand-blue text-white px-3 py-2 text-xs font-semibold"
            >
              <Plus size={14} /> નવું પ્રકરણ
            </button>
          )}
        </div>
      </div>

      {showForm && selected && (
        <div className="bg-white rounded-2xl shadow-card p-4 grid grid-cols-2 md:grid-cols-4 gap-3 items-end">
          <div>
            <label className="text-xs text-navy-500">ક્રમ</label>
            <input
              type="number"
              value={form.number}
              onChange={(e) => setForm({ ...form, number: +e.target.value })}
              className="mt-1 w-full rounded-lg border border-navy-100 px-2 py-2 text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-navy-500">નામ (ગુજરાતી)</label>
            <input
              value={form.name_gu}
              onChange={(e) => setForm({ ...form, name_gu: e.target.value })}
              className="mt-1 w-full rounded-lg border border-navy-100 px-2 py-2 text-sm"
              placeholder="પ્રકાશ"
            />
          </div>
          <div>
            <label className="text-xs text-navy-500">Name (EN)</label>
            <input
              value={form.name_en}
              onChange={(e) => setForm({ ...form, name_en: e.target.value })}
              className="mt-1 w-full rounded-lg border border-navy-100 px-2 py-2 text-sm"
              placeholder="Light"
            />
          </div>
          <button onClick={create} className="rounded-lg bg-brand-green text-white py-2 text-sm font-semibold">
            ઉમેરો
          </button>
        </div>
      )}

      <div className="bg-white rounded-2xl shadow-card divide-y divide-navy-50">
        {chapters.map((c) => (
          <div key={c.id} className="flex items-center gap-3 px-4 py-3">
            <span className="w-8 h-8 rounded-full bg-navy-50 text-navy-700 text-sm font-bold flex items-center justify-center">
              {c.number}
            </span>
            <div className="flex-1">
              <div className="text-sm font-medium text-navy-900">{c.name_gu}</div>
              <div className="text-xs text-navy-400">{c.name_en}</div>
            </div>
            <button onClick={() => remove(c.id)} className="p-2 rounded-lg text-red-400 hover:bg-red-50">
              <Trash2 size={15} />
            </button>
          </div>
        ))}
        {!selected && (
          <div className="text-center text-sm text-navy-400 py-8">પ્રથમ વિષય પસંદ કરો.</div>
        )}
        {selected && chapters.length === 0 && (
          <div className="text-center text-sm text-navy-400 py-8">
            {subject?.name_gu} માં કોઈ પ્રકરણ નથી.
          </div>
        )}
      </div>
    </div>
  )
}
