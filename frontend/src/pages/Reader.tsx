import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowUp, MessageCircleQuestion, Sparkles, X } from 'lucide-react'
import { api, apiStream } from '../services/api'
import type { Chapter, Subject } from '../types'
import Markdown from '../components/Markdown'

interface ReaderSection {
  section: string
  heading?: string
  order: number
}


/** Very small markdown subset renderer: **bold**, headings, list items. */
function renderInline(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/\*\*(.+?)\*\*/g, '<b>$1</b>')
    .replace(/\*(.+?)\*/g, '<i>$1</i>')
    .replace(/^### (.*)$/gm, '<h3>$1</h3>')
    .replace(/^## (.*)$/gm, '<h2>$1</h2>')
}

function SectionHtml({ text }: { text: string }) {
  const html = renderInline(text)
    .split('\n')
    .map((line) => {
      const t = line.trim()
      if (t.startsWith('<h2') || t.startsWith('<h3')) return line
      if (/^[-*•]\s+/.test(t)) return `<li>${t.replace(/^[-*•]\s+/, '')}</li>`
      if (/^\d+[.)]\s+/.test(t)) return `<li>${t.replace(/^\d+[.)]\s+/, '')}</li>`
      if (!t) return ''
      return `<p>${t}</p>`
    })
    .join('\n')
  return <div className="reader-prose" dangerouslySetInnerHTML={{ __html: html }} />
}

export default function Reader() {
  const { chapterId } = useParams()
  const navigate = useNavigate()
  const [chapter, setChapter] = useState<Chapter | null>(null)
  const [subject, setSubject] = useState<Subject | null>(null)
  const [sections, setSections] = useState<ReaderSection[]>([])
  const [loading, setLoading] = useState(true)
  const [notReady, setNotReady] = useState(false)

  // Floating chatbot state
  const [chatOpen, setChatOpen] = useState(false)
  const [messages, setMessages] = useState<{ role: string; content: string; pending?: boolean }[]>([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!chapterId) return
    setLoading(true)
    api<{ chapter: Chapter; subject: Subject | null; sections: string[] }>(
      `/api/chapters/${chapterId}/content`
    )
      .then((r) => {
        setChapter(r.chapter)
        setSubject(r.subject)
        setSections(r.sections.map((section, order) => ({ section, order })))
        setNotReady(r.sections.length === 0)
      })
      .catch(() => setNotReady(true))
      .finally(() => setLoading(false))
  }, [chapterId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const ask = async (question: string) => {
    if (!question.trim() || streaming) return
    setMessages((m) => [...m, { role: 'user', content: question }])
    setInput('')
    setStreaming(true)
    const aiIdx = messages.length + 1
    setMessages((m) => [...m, { role: 'assistant', content: '', pending: true }])
    await apiStream(
      '/api/chat/stream',
      {
        conversation_id: null,
        message: question,
        mode: 'ask',
        subject_id: subject?.id || null,
        chapter_id: chapterId || null,
      },
      (delta) => {
        setMessages((m) => m.map((msg, i) => (i === aiIdx ? { ...msg, content: msg.content + delta } : msg)))
      },
      (meta) => {
        setStreaming(false)
        setMessages((m) => m.map((msg, i) => (i === aiIdx ? { ...msg, pending: false } : msg)))
        void meta
      },
      (err) => {
        setStreaming(false)
        setMessages((m) =>
          m.map((msg, i) => (i === aiIdx ? { ...msg, pending: false, content: msg.content || `⚠️ ${err}` } : msg))
        )
      }
    )
  }

  const quickQuestions = [
    'આ પ્રકરણ સરળ ભાષામાં સમજાવો',
    'મહત્વના પ્રશ્નો બતાવો',
    'પરીક્ષામાં શું પૂછાય છે?',
  ]

  return (
    <div className="max-w-3xl mx-auto px-4 py-6 pb-28">
      {loading && <div className="text-sm text-navy-400 text-center py-16">લોડ થાય છે…</div>}

      {!loading && notReady && (
        <div className="bg-white rounded-2xl shadow-card p-8 text-center">
          <div className="text-3xl">📖</div>
          <div className="mt-2 font-bold text-navy-900">આ પ્રકરણનું વાંચન સામગ્રી ટૂંક સમયમાં</div>
          <p className="text-xs text-navy-400 mt-1">
            જ્યારે સામગ્રી ઉમેરાશે, ત્યારે અહીં વાંચી શકાશે. ત્યાં સુધી AI સાથીને પ્રશ્ન પૂછી શકો છો.
          </p>
          <button
            onClick={() => setChatOpen(true)}
            className="mt-4 rounded-xl bg-brand-orange text-white px-4 py-2 text-sm font-semibold"
          >
            AI સાથીને પૂછો
          </button>
        </div>
      )}

      {!loading && !notReady && (
        <>
          <div className="bg-gradient-to-br from-navy-900 to-brand-blue rounded-2xl p-5 text-white mb-6">
            <div className="text-xs text-white/70">{subject?.name_gu || ''} · ધોરણ 10</div>
            <h1 className="text-xl font-extrabold mt-1">
              પ્રકરણ {chapter?.number}: {chapter?.name_gu}
            </h1>
          </div>

          <div className="space-y-4">
            {sections.map((s, i) => (
              <div
                key={i}
                className="reader-fade-up bg-white rounded-2xl shadow-card p-5"
                style={{ ['--fade-delay' as string]: `${Math.min(i * 90, 900)}ms` }}
              >
                {s.heading && (
                  <h2 className="font-bold text-navy-900 mb-2 text-base">{s.heading}</h2>
                )}
                <SectionHtml text={s.section} />
              </div>
            ))}
          </div>
        </>
      )}

      {/* Floating AI chatbot */}
      <div className="fixed bottom-20 right-4 z-40 md:bottom-6">
        {chatOpen && (
          <div className="mb-3 w-[min(92vw,22rem)] h-[28rem] bg-white rounded-2xl shadow-card-hover border border-navy-100 flex flex-col overflow-hidden">
            <div className="bg-navy-900 text-white px-4 py-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles size={16} className="text-brand-orange" />
                <div>
                  <div className="text-sm font-bold">AI સાથી</div>
                  <div className="text-[10px] text-white/60">
                    {chapter ? `પ્રકરણ ${chapter.number} · ${chapter.name_gu}` : 'તમારો અભ્યાસ સાથી'}
                  </div>
                </div>
              </div>
              <button onClick={() => setChatOpen(false)} aria-label="બંધ કરો">
                <X size={18} />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-3 space-y-2.5 bg-slate-50">
              {messages.length === 0 && (
                <div className="space-y-2">
                  <p className="text-xs text-navy-400 text-center py-2">આ પ્રકરણ વિશે પૂછો:</p>
                  {quickQuestions.map((q) => (
                    <button
                      key={q}
                      onClick={() => ask(q)}
                      className="w-full text-left text-xs bg-white border border-navy-100 rounded-xl px-3 py-2 hover:border-brand-blue transition"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              )}
              {messages.map((m, i) => (
                <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div
                    className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm ${
                      m.role === 'user'
                        ? 'bg-brand-blue text-white rounded-br-sm'
                        : 'bg-white border border-navy-100 rounded-bl-sm'
                    }`}
                  >
                    {m.role === 'assistant' ? (
                      m.pending && !m.content ? (
                        <span className="text-navy-300">લખી રહ્યો છું…</span>
                      ) : (
                        <Markdown text={m.content} />
                      )
                    ) : (
                      m.content
                    )}
                  </div>
                </div>
              ))}
              <div ref={bottomRef} />
            </div>

            <div className="p-2.5 border-t border-navy-100 bg-white">
              <div className="flex items-center gap-2">
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && ask(input)}
                  placeholder="શંકા પૂછો…"
                  className="flex-1 rounded-xl border border-navy-100 px-3 py-2 text-sm outline-none focus:border-brand-blue"
                />
                <button
                  onClick={() => ask(input)}
                  disabled={!input.trim() || streaming}
                  className="rounded-xl bg-brand-orange text-white p-2.5 disabled:opacity-40"
                  aria-label="મોકલો"
                >
                  <ArrowUp size={16} />
                </button>
              </div>
            </div>
          </div>
        )}

        <button
          onClick={() => setChatOpen((o) => !o)}
          className={`chat-float-btn ml-auto flex items-center justify-center w-14 h-14 rounded-full bg-brand-orange text-white shadow-lg transition-transform hover:scale-105 ${
            chatOpen ? 'rotate-45' : ''
          }`}
          aria-label="AI ચેટ"
        >
          {chatOpen ? <X size={24} /> : <MessageCircleQuestion size={26} />}
        </button>
      </div>
    </div>
  )
}
