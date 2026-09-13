import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { MessageSquare, Pencil, Search, Trash2 } from 'lucide-react'
import { api } from '../services/api'
import type { Conversation } from '../types'

export default function History() {
  const navigate = useNavigate()
  const [chats, setChats] = useState<Conversation[]>([])
  const [query, setQuery] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editTitle, setEditTitle] = useState('')

  const load = () => api<{ chats: Conversation[] }>('/api/chats').then((r) => setChats(r.chats))

  useEffect(() => {
    load().catch(() => {})
  }, [])

  const rename = async (id: string) => {
    if (!editTitle.trim()) return
    await api(`/api/chats/${id}`, { method: 'PATCH', body: JSON.stringify({ title: editTitle.trim() }) })
    setEditingId(null)
    load()
  }

  const remove = async (id: string) => {
    if (!confirm('આ સંવાદ ડિલીટ કરવો છે?')) return
    await api(`/api/chats/${id}`, { method: 'DELETE' })
    load()
  }

  const filtered = chats.filter((c) => c.title.toLowerCase().includes(query.toLowerCase()))

  return (
    <div className="max-w-3xl mx-auto px-4 py-6">
      <h1 className="text-lg font-bold text-navy-900 mb-4">ચેટ ઇતિહાસ</h1>
      <div className="flex items-center gap-2 rounded-xl bg-white border border-navy-100 px-3 py-2.5 mb-4">
        <Search size={17} className="text-navy-300" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="સંવાદ શોધો…"
          className="flex-1 text-sm outline-none"
        />
      </div>
      <div className="space-y-2">
        {filtered.map((c) => (
          <div key={c.id} className="bg-white rounded-2xl shadow-card p-3.5 flex items-center gap-3">
            <MessageSquare size={18} className="text-brand-orange shrink-0" />
            {editingId === c.id ? (
              <input
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && rename(c.id)}
                className="flex-1 text-sm rounded-lg border border-brand-blue px-2 py-1 outline-none"
                autoFocus
              />
            ) : (
              <button onClick={() => navigate(`/chat/${c.id}`)} className="flex-1 text-left min-w-0">
                <div className="text-sm font-medium text-navy-900 truncate">{c.title}</div>
                <div className="text-[11px] text-navy-400">
                  {c.updated_at ? new Date(c.updated_at).toLocaleString('gu-IN') : ''}
                </div>
              </button>
            )}
            {editingId === c.id ? (
              <button onClick={() => rename(c.id)} className="text-xs text-brand-green font-semibold">
                સેવ ✓
              </button>
            ) : (
              <button
                onClick={() => {
                  setEditingId(c.id)
                  setEditTitle(c.title)
                }}
                className="p-2 rounded-lg text-navy-400 hover:bg-navy-50"
              >
                <Pencil size={15} />
              </button>
            )}
            <button onClick={() => remove(c.id)} className="p-2 rounded-lg text-red-400 hover:bg-red-50">
              <Trash2 size={15} />
            </button>
          </div>
        ))}
        {filtered.length === 0 && (
          <div className="text-center text-sm text-navy-400 bg-white rounded-2xl p-8 shadow-card">
            કોઈ સંવાદ નથી. Gyan Sathi ને પ્રશ્ન પૂછીને શરૂ કરો!
          </div>
        )}
      </div>
    </div>
  )
}
