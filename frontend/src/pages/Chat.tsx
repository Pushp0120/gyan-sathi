import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  BookMarked, Check, ChevronLeft, Copy, FileUp, ListChecks, Menu, MessagesSquare,
  Plus, RefreshCw, Send, Sparkles, ThumbsDown, ThumbsUp, X,
} from 'lucide-react'
import { api, apiStream } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import type { ChatMessage, Chapter, Conversation, RagSource, Subject } from '../types'
import Markdown from '../components/Markdown'
import Logo from '../components/Logo'

const MODES = [
  { id: 'ask', label: 'પૂછો', icon: Sparkles },
  { id: 'explain', label: 'સરળ સમજૂતી', icon: BookMarked },
  { id: 'exam', label: 'પરીક્ષા જવાબ', icon: ListChecks },
  { id: 'summary', label: 'સાર', icon: BookMarked },
  { id: 'mcq', label: 'MCQ', icon: ListChecks },
  { id: 'practice', label: 'પ્રેક્ટિસ', icon: RefreshCw },
  { id: 'important', label: 'મહત્વના પ્રશ્નો', icon: FileUp },
]

export default function Chat() {
  const { conversationId } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [params] = useSearchParams()

  const [subjects, setSubjects] = useState<Subject[]>([])
  const [chapters, setChapters] = useState<Chapter[]>([])
  const [subjectId, setSubjectId] = useState('')
  const [chapterId, setChapterId] = useState('')
  const [mode, setMode] = useState(params.get('mode') || 'ask')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const [uploadInfo, setUploadInfo] = useState<string>('')
  const fileRef = useRef<HTMLInputElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    api<{ subjects: Subject[] }>(`/api/subjects?standard=${user?.standard}`)
      .then((r) => setSubjects(r.subjects))
      .catch(() => {})
    api<{ chats: Conversation[] }>('/api/chats')
      .then((r) => setConversations(r.chats))
      .catch(() => {})
  }, [user?.standard])

  useEffect(() => {
    if (!subjectId) {
      setChapters([])
      return
    }
    api<{ chapters: Chapter[] }>(`/api/subjects/${subjectId}/chapters`)
      .then((r) => setChapters(r.chapters))
      .catch(() => {})
  }, [subjectId])

  useEffect(() => {
    if (conversationId) {
      api<Conversation & { messages: ChatMessage[] }>(`/api/chats/${conversationId}`)
        .then((c) => {
          setMessages(c.messages)
          if (c.subject_id) setSubjectId(c.subject_id)
        })
        .catch(() => {})
    } else {
      setMessages([])
    }
  }, [conversationId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const newChat = () => {
    setMessages([])
    navigate('/chat')
    setDrawerOpen(false)
  }

  const send = useCallback(
    async (text?: string) => {
      const question = (text ?? input).trim()
      if (!question || streaming) return
      setInput('')
      setStreaming(true)

      const userMsg: ChatMessage = {
        id: `tmp-${Date.now()}`, role: 'user', content: question, mode,
        sources: [], used_rag: false, feedback: null, created_at: null,
      }
      const aiMsg: ChatMessage = {
        id: `tmp-ai-${Date.now()}`, role: 'assistant', content: '', mode,
        sources: [], used_rag: false, feedback: null, created_at: null, pending: true,
      }
      setMessages((m) => [...m, userMsg, aiMsg])

      await apiStream(
        '/api/chat/stream',
        {
          conversation_id: conversationId || null,
          message: question,
          mode,
          subject_id: subjectId || null,
          chapter_id: chapterId || null,
        },
        (delta) => {
          setMessages((m) =>
            m.map((msg) => (msg.id === aiMsg.id ? { ...msg, content: msg.content + delta } : msg))
          )
        },
        (meta) => {
          setStreaming(false)
          if (meta?.conversation_id && meta.conversation_id !== conversationId) {
            navigate(`/chat/${meta.conversationId || meta.conversation_id}`, { replace: true })
          }
          setMessages((m) =>
            m.map((msg) =>
              msg.id === aiMsg.id
                ? { ...msg, pending: false, sources: meta?.sources || [], used_rag: !!meta?.used_rag }
                : msg
            )
          )
        },
        (err) => {
          setStreaming(false)
          setMessages((m) =>
            m.map((msg) =>
              msg.id === aiMsg.id
                ? { ...msg, pending: false, content: msg.content || `⚠️ ${err}` }
                : msg
            )
          )
        }
      )
    },
    [input, streaming, mode, conversationId, subjectId, chapterId, navigate]
  )

  const regenerate = () => {
    const lastUser = [...messages].reverse().find((m) => m.role === 'user')
    if (lastUser) send(lastUser.content)
  }

  const feedback = async (messageId: string, rating: 'up' | 'down') => {
    setMessages((m) => m.map((x) => (x.id === messageId ? { ...x, feedback: rating } : x)))
    try {
      await api('/api/feedback', { method: 'POST', body: JSON.stringify({ message_id: messageId, rating }) })
    } catch {}
  }

  const onUpload = async (file: File) => {
    setUploadInfo('અપલોડ થઈ રહ્યું છે…')
    const fd = new FormData()
    fd.append('file', file)
    try {
      const res = await api<{ upload: any; allowance: any }>('/api/uploads', { method: 'POST', body: fd })
      setUploadInfo(`✓ ${file.name} અપલોડ થયું (વપરાયેલ ${res.allowance.used}/${res.allowance.limit})`)
      setInput((prev) => prev || 'આ ફાઇલનું વિશ્લેષણ કરીને સમજાવો.')
    } catch (e: any) {
      if (e.status === 402) {
        setUploadInfo('')
        if (confirm('તમારા 10 મફત uploads પૂર્ણ થઈ ગયા છે. Premium લેવા જઈએ?')) navigate('/premium')
      } else {
        setUploadInfo(`⚠️ ${e.message}`)
      }
    }
  }

  const copy = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  return (
    <div className="flex h-[calc(100%-0px)]">
      {/* History drawer */}
      {drawerOpen && (
        <div className="fixed inset-0 z-40 flex md:hidden" onClick={() => setDrawerOpen(false)}>
          <div className="flex-1 bg-black/40" />
          <div className="w-72 bg-white h-full overflow-y-auto p-4 space-y-1" onClick={(e) => e.stopPropagation()}>
            <button onClick={newChat} className="w-full flex items-center gap-2 rounded-xl bg-brand-blue text-white py-2.5 px-3 text-sm font-semibold">
              <Plus size={16} /> નવો સંવાદ
            </button>
            {conversations.map((c) => (
              <button
                key={c.id}
                onClick={() => {
                  navigate(`/chat/${c.id}`)
                  setDrawerOpen(false)
                }}
                className="w-full text-left rounded-lg px-3 py-2 text-sm text-navy-700 hover:bg-navy-50 truncate"
              >
                {c.title}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="flex-1 flex flex-col min-w-0">
        {/* Chat header */}
        <div className="sticky top-0 z-10 bg-white/95 backdrop-blur border-b border-navy-100 px-3 py-2">
          <div className="flex items-center gap-2">
            <button className="md:hidden p-1.5 rounded-lg hover:bg-navy-50" onClick={() => setDrawerOpen(true)}>
              <Menu size={20} />
            </button>
            {conversationId && (
              <button className="p-1.5 rounded-lg hover:bg-navy-50" onClick={newChat} aria-label="back">
                <ChevronLeft size={20} />
              </button>
            )}
            <Logo size={30} withText={false} />
            <select
              value={subjectId}
              onChange={(e) => {
                setSubjectId(e.target.value)
                setChapterId('')
              }}
              className="text-xs rounded-lg border border-navy-100 px-2 py-1.5 bg-white max-w-[9rem]"
            >
              <option value="">વિષય: બધા</option>
              {subjects.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.icon} {s.name_gu}
                </option>
              ))}
            </select>
            <select
              value={chapterId}
              onChange={(e) => setChapterId(e.target.value)}
              disabled={!chapters.length}
              className="text-xs rounded-lg border border-navy-100 px-2 py-1.5 bg-white max-w-[9rem] disabled:opacity-50"
            >
              <option value="">પ્રકરણ: બધું</option>
              {chapters.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.number}. {c.name_gu}
                </option>
              ))}
            </select>
            <button onClick={newChat} className="ml-auto flex items-center gap-1 rounded-lg bg-navy-50 text-navy-700 px-2.5 py-1.5 text-xs font-semibold hover:bg-navy-100">
              <Plus size={14} /> નવો
            </button>
          </div>
          {/* Mode chips */}
          <div className="mt-2 flex gap-1.5 overflow-x-auto pb-0.5">
            {MODES.map((m) => (
              <button
                key={m.id}
                onClick={() => setMode(m.id)}
                className={`shrink-0 flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium border transition ${
                  mode === m.id
                    ? 'bg-brand-blue text-white border-brand-blue'
                    : 'bg-white text-navy-500 border-navy-100 hover:border-navy-200'
                }`}
              >
                <m.icon size={12} />
                {m.label}
              </button>
            ))}
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-3 md:px-6 py-4 space-y-4">
          {messages.length === 0 && (
            <div className="max-w-md mx-auto text-center py-10 space-y-3">
              <Logo size={84} withText={false} className="justify-center" />
              <h2 className="text-lg font-bold text-navy-900">નમસ્તે! હું Gyan Sathi છું 👋</h2>
              <p className="text-sm text-navy-500">
                ગુજરાતીમાં કોઈપણ પ્રશ્ન પૂછો — ધોરણ {user?.standard} ના અભ્યાસક્રમ પ્રમાણે જવાબ મળશે.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2">
                {['ન્યુટનનો પ્રથમ નિયમ સમજાવો', 'પ્રકાશનું પરાવર્તન શું છે?', 'પાયથાગોરસનો પ્રમેય', 'ત્રિકોણમિતિના સૂત્રો'].map((q) => (
                  <button
                    key={q}
                    onClick={() => send(q)}
                    className="rounded-xl bg-white border border-navy-100 px-3 py-2.5 text-xs text-navy-700 hover:border-brand-blue hover:text-brand-blue transition text-left"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m) => (
            <div key={m.id} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`max-w-[92%] md:max-w-[80%] rounded-2xl px-4 py-3 text-sm shadow-card ${
                  m.role === 'user'
                    ? 'bg-brand-blue text-white rounded-br-md'
                    : 'bg-white text-navy-900 rounded-bl-md border border-navy-100'
                }`}
              >
                {m.role === 'assistant' ? (
                  <>
                    {m.content ? (
                      <Markdown text={m.content} />
                    ) : (
                      <div className="flex items-center gap-2 text-navy-400">
                        <span className="animate-pulse">Gyan Sathi વિચારે છે…</span>
                      </div>
                    )}
                    {m.sources && m.sources.length > 0 && (
                      <div className="mt-3 rounded-xl bg-navy-50 px-3 py-2 text-xs text-navy-600 space-y-1">
                        {m.sources.slice(0, 3).map((s: RagSource, i: number) => (
                          <div key={i} className="flex items-center gap-1.5">
                            <BookMarked size={12} className="text-brand-orange shrink-0" />
                            <span>
                              {s.standard ? `ધોરણ ${s.standard}` : ''} {s.subject_gu || ''}
                              {s.chapter_gu ? ` · પ્રકરણ: ${s.chapter_gu}` : ''}
                              {s.page_number ? ` · પાનું ${s.page_number}` : ''}
                            </span>
                          </div>
                        ))}
                        <div className="text-[10px] text-navy-400">📚 સ્ત્રોત: Gyan Sathi જ્ઞાન કોશ</div>
                      </div>
                    )}
                    {!m.pending && m.content && (
                      <div className="mt-2 flex items-center gap-1 border-t border-navy-50 pt-2">
                        <button onClick={() => copy(m.content)} className="p-1.5 rounded-lg hover:bg-navy-50 text-navy-400" title="Copy">
                          <Copy size={14} />
                        </button>
                        <button onClick={regenerate} className="p-1.5 rounded-lg hover:bg-navy-50 text-navy-400" title="Regenerate">
                          <RefreshCw size={14} />
                        </button>
                        <button
                          onClick={() => feedback(m.id, 'up')}
                          className={`p-1.5 rounded-lg hover:bg-navy-50 ${m.feedback === 'up' ? 'text-brand-green' : 'text-navy-400'}`}
                          title="મદદરૂપ"
                        >
                          {m.feedback === 'up' ? <Check size={14} /> : <ThumbsUp size={14} />}
                        </button>
                        <button
                          onClick={() => feedback(m.id, 'down')}
                          className={`p-1.5 rounded-lg hover:bg-navy-50 ${m.feedback === 'down' ? 'text-red-500' : 'text-navy-400'}`}
                          title="મદદરૂપ નથી"
                        >
                          {m.feedback === 'down' ? <X size={14} /> : <ThumbsDown size={14} />}
                        </button>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="whitespace-pre-wrap">{m.content}</div>
                )}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        {/* Composer */}
        <div className="border-t border-navy-100 bg-white px-3 py-2.5">
          {uploadInfo && (
            <div className="mb-1.5 text-[11px] text-navy-500 flex items-center gap-1">
              {uploadInfo}
              <button onClick={() => setUploadInfo('')}><X size={11} /></button>
            </div>
          )}
          <div className="flex items-end gap-2 max-w-3xl mx-auto">
            <input
              ref={fileRef}
              type="file"
              hidden
              accept=".pdf,.png,.jpg,.jpeg,.txt,.md,.docx"
              onChange={(e) => e.target.files?.[0] && onUpload(e.target.files[0])}
            />
            <button
              onClick={() => fileRef.current?.click()}
              className="p-2.5 rounded-xl text-navy-400 hover:bg-navy-50 hover:text-navy-600"
              title="ફાઇલ અપલોડ"
            >
              <FileUp size={19} />
            </button>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  send()
                }
              }}
              rows={1}
              placeholder="ગુજરાતીમાં પ્રશ્ન લખો… (Shift+Enter = નવી લાઇન)"
              className="flex-1 resize-none rounded-xl border border-navy-100 px-3.5 py-2.5 text-sm outline-none focus:border-brand-blue max-h-32"
            />
            <button
              onClick={() => send()}
              disabled={!input.trim() || streaming}
              className="p-2.5 rounded-xl bg-brand-blue text-white hover:bg-navy-800 disabled:opacity-40"
            >
              <Send size={19} />
            </button>
          </div>
          <div className="text-center text-[10px] text-navy-300 mt-1">
            Gyan Sathi ભૂલો કરી શકે છે — મહત્વની વિગતો પાઠ્યપુસ્તકથી ચકાસો.
          </div>
        </div>
      </div>
    </div>
  )
}
