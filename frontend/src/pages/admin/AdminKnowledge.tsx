import { useCallback, useEffect, useRef, useState } from 'react'
import { Database, RefreshCw, Search, Trash2, UploadCloud } from 'lucide-react'
import { api } from '../../services/api'
import type { Chapter, Subject } from '../../types'

interface Doc {
  id: string
  title: string
  source_type: string
  standard: number
  subject_id: string | null
  chapter_id: string | null
  status: string
  chunk_count: number
  is_enabled: boolean
  file_name: string
  error_message: string
  created_at: string | null
}

const STATUS_STYLE: Record<string, string> = {
  pending: 'bg-slate-100 text-slate-600',
  processing: 'bg-amber-100 text-amber-700',
  completed: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-600',
}

export default function AdminKnowledge() {
  const [docs, setDocs] = useState<Doc[]>([])
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [chapters, setChapters] = useState<Chapter[]>([])
  const [form, setForm] = useState({
    title: '',
    standard: 10,
    subject_id: '',
    chapter_id: '',
    source_type: 'curated',
  })
  const [busy, setBusy] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<any[]>([])
  const fileRef = useRef<HTMLInputElement>(null)

  const load = useCallback(() => {
    api<{ documents: Doc[] }>('/api/admin/knowledge')
      .then((r) => setDocs(r.documents))
      .catch(() => {})
  }, [])

  useEffect(() => {
    load()
    api<{ subjects: Subject[] }>('/api/subjects').then((r) => setSubjects(r.subjects)).catch(() => {})
  }, [load])

  useEffect(() => {
    if (!form.subject_id) return setChapters([])
    api<{ chapters: Chapter[] }>(`/api/subjects/${form.subject_id}/chapters`)
      .then((r) => setChapters(r.chapters))
      .catch(() => {})
  }, [form.subject_id])

  const upload = async (file: File) => {
    setBusy(true)
    const fd = new FormData()
    fd.append('file', file)
    fd.append('title', form.title || file.name)
    fd.append('standard', String(form.standard))
    if (form.subject_id) fd.append('subject_id', form.subject_id)
    if (form.chapter_id) fd.append('chapter_id', form.chapter_id)
    fd.append('source_type', form.source_type)
    try {
      await api('/api/admin/knowledge/upload', { method: 'POST', body: fd })
      setForm({ ...form, title: '' })
      load()
    } catch (e: any) {
      alert(e.message)
    } finally {
      setBusy(false)
    }
  }

  const reprocess = async (id: string) => {
    setBusy(true)
    try {
      await api(`/api/admin/knowledge/${id}/reprocess`, { method: 'POST' })
      load()
    } catch (e: any) {
      alert(e.message)
    } finally {
      setBusy(false)
    }
  }

  const toggle = async (doc: Doc) => {
    await api(`/api/admin/knowledge/${doc.id}`, {
      method: 'PATCH',
      body: JSON.stringify({ is_enabled: !doc.is_enabled }),
    })
    load()
  }

  const remove = async (id: string) => {
    if (!confirm('દસ્તાવેજ અને બધી છૂંકીઓ ડિલીટ થશે. ચાલુ રાખવું?')) return
    await api(`/api/admin/knowledge/${id}`, { method: 'DELETE' })
    load()
  }

  const search = async () => {
    if (!searchQuery.trim()) return
    const r = await api<{ results: any[] }>('/api/admin/knowledge/search', {
      method: 'POST',
      body: JSON.stringify({ query: searchQuery, standard: null, top_k: 5 }),
    })
    setSearchResults(r.results)
  }

  return (
    <div className="p-4 md:p-6 space-y-4">
      <h1 className="text-lg font-bold text-navy-900">જ્ઞાન કોશ (Knowledge Base)</h1>

      {/* Upload */}
      <div className="bg-white rounded-2xl shadow-card p-4 space-y-3">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <div className="col-span-2">
            <label className="text-xs text-navy-500">શીર્ષક</label>
            <input
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              placeholder="દા.ત. વિજ્ઞાન પ્રકરણ 10 નોટ્સ"
              className="mt-1 w-full rounded-lg border border-navy-100 px-2 py-2 text-sm"
            />
          </div>
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
            <label className="text-xs text-navy-500">વિષય</label>
            <select
              value={form.subject_id}
              onChange={(e) => setForm({ ...form, subject_id: e.target.value, chapter_id: '' })}
              className="mt-1 w-full rounded-lg border border-navy-100 px-2 py-2 text-sm bg-white"
            >
              <option value="">— પસંદ કરો —</option>
              {subjects
                .filter((s) => s.standard === form.standard)
                .map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name_gu}
                  </option>
                ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-navy-500">પ્રકરણ</label>
            <select
              value={form.chapter_id}
              onChange={(e) => setForm({ ...form, chapter_id: e.target.value })}
              disabled={!chapters.length}
              className="mt-1 w-full rounded-lg border border-navy-100 px-2 py-2 text-sm bg-white disabled:opacity-50"
            >
              <option value="">— પસંદ કરો —</option>
              {chapters.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.number}. {c.name_gu}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={form.source_type}
            onChange={(e) => setForm({ ...form, source_type: e.target.value })}
            className="rounded-lg border border-navy-100 px-2 py-2 text-sm bg-white"
          >
            <option value="gseb">GSEB સત્તાવાર</option>
            <option value="textbook">પાઠ્યપુસ્તક</option>
            <option value="question_bank">પ્રશ્નબેંક</option>
            <option value="curated">ક્યૂરેટેડ</option>
            <option value="demo">ડેમો</option>
          </select>
          <input
            ref={fileRef}
            type="file"
            hidden
            accept=".pdf,.txt,.md,.docx"
            onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])}
          />
          <button
            onClick={() => fileRef.current?.click()}
            disabled={busy}
            className="flex items-center gap-2 rounded-xl bg-brand-blue text-white px-4 py-2 text-sm font-semibold disabled:opacity-50"
          >
            <UploadCloud size={16} /> {busy ? 'પ્રક્રિયા ચાલુ…' : 'દસ્તાવેજ અપલોડ કરો'}
          </button>
          <span className="text-[11px] text-navy-400">PDF, TXT, MD, DOCX — ઓટોમેટિક છૂંકીંગ + embeddings</span>
        </div>
      </div>

      {/* Semantic search */}
      <div className="bg-white rounded-2xl shadow-card p-4">
        <div className="flex gap-2">
          <div className="flex-1 flex items-center gap-2 rounded-xl border border-navy-100 px-3">
            <Search size={15} className="text-navy-300" />
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && search()}
              placeholder="જ્ઞાન કોશમાં શું છે તે ચકાસો (semantic search)…"
              className="flex-1 py-2 text-sm outline-none"
            />
          </div>
          <button onClick={search} className="rounded-xl bg-navy-900 text-white px-4 text-sm font-semibold">
            શોધો
          </button>
        </div>
        {searchResults.length > 0 && (
          <div className="mt-3 space-y-2">
            {searchResults.map((r, i) => (
              <div key={i} className="rounded-xl bg-navy-50 px-3 py-2 text-xs">
                <div className="font-semibold text-navy-700">
                  ધોરણ {r.standard} · {r.subject_name_gu} · {r.chapter_name_gu}
                  {r.page_number ? ` · પાનું ${r.page_number}` : ''}{' '}
                  <span className="text-navy-400">(distance: {Number(r.distance).toFixed(3)})</span>
                </div>
                <div className="text-navy-600 line-clamp-2 mt-0.5">{r.content.slice(0, 180)}…</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Documents list */}
      <div className="space-y-2">
        {docs.map((d) => (
          <div key={d.id} className="bg-white rounded-2xl shadow-card p-4 flex flex-wrap items-center gap-3">
            <Database size={18} className="text-brand-blue shrink-0" />
            <div className="flex-1 min-w-[200px]">
              <div className="text-sm font-semibold text-navy-900">{d.title}</div>
              <div className="text-[11px] text-navy-400">
                ધોરણ {d.standard} · {d.chunk_count} છૂંકીઓ · {d.source_type} ·{' '}
                {d.created_at ? new Date(d.created_at).toLocaleDateString('gu-IN') : ''}
                {d.error_message && <span className="text-red-400"> · {d.error_message.slice(0, 60)}</span>}
              </div>
            </div>
            <span className={`rounded-full px-2.5 py-1 text-[11px] font-bold ${STATUS_STYLE[d.status] || ''}`}>
              {d.status}
            </span>
            <button
              onClick={() => toggle(d)}
              className={`rounded-full px-2.5 py-1 text-[11px] font-bold ${
                d.is_enabled ? 'bg-navy-50 text-navy-600' : 'bg-slate-100 text-slate-400'
              }`}
            >
              {d.is_enabled ? 'ચાલુ' : 'બંધ'}
            </button>
            <button onClick={() => reprocess(d.id)} className="p-2 rounded-lg text-navy-400 hover:bg-navy-50" title="ફરી પ્રોસેસ">
              <RefreshCw size={15} />
            </button>
            <button onClick={() => remove(d.id)} className="p-2 rounded-lg text-red-400 hover:bg-red-50">
              <Trash2 size={15} />
            </button>
          </div>
        ))}
        {docs.length === 0 && (
          <div className="text-center text-sm text-navy-400 bg-white rounded-2xl p-8 shadow-card">
            હજી કોઈ દસ્તાવેજ નથી. ઉપરથી અપલોડ કરો.
          </div>
        )}
      </div>
    </div>
  )
}
