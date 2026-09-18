import { useEffect, useRef, useState } from 'react'
import { ArrowUp, MessageCircleQuestion, Sparkles, X } from 'lucide-react'
import { apiStream } from '../services/api'
import Markdown from './Markdown'

interface FloatingChatProps {
  /** Shown in the chat header, e.g. "પ્રકરણ 3 · ધ્રુવો" or "વિજ્ઞાન" */
  contextLabel?: string
  subjectId?: string | null
  chapterId?: string | null
  quickQuestions?: string[]
}

const DEFAULT_QUESTIONS = [
  'આ વિષય સરળ ભાષામાં સમજાવો',
  'મહત્વના પ્રશ્નો બતાવો',
  'પરીક્ષામાં શું પૂછાય છે?',
]

export default function FloatingChat({
  contextLabel,
  subjectId,
  chapterId,
  quickQuestions,
}: FloatingChatProps) {
  const [chatOpen, setChatOpen] = useState(false)
  const [messages, setMessages] = useState<{ role: string; content: string; pending?: boolean }[]>([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

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
        subject_id: subjectId || null,
        chapter_id: chapterId || null,
      },
      (delta) => {
        setMessages((m) => m.map((msg, i) => (i === aiIdx ? { ...msg, content: msg.content + delta } : msg)))
      },
      () => {
        setStreaming(false)
        setMessages((m) => m.map((msg, i) => (i === aiIdx ? { ...msg, pending: false } : msg)))
      },
      (err) => {
        setStreaming(false)
        setMessages((m) =>
          m.map((msg, i) => (i === aiIdx ? { ...msg, pending: false, content: msg.content || `⚠️ ${err}` } : msg))
        )
      }
    )
  }

  const questions = quickQuestions || DEFAULT_QUESTIONS

  return (
    <div className="fixed bottom-20 right-4 z-40 md:bottom-6">
      {chatOpen && (
        <div className="mb-3 w-[min(92vw,22rem)] h-[28rem] bg-white rounded-2xl shadow-card-hover border border-navy-100 flex flex-col overflow-hidden">
          <div className="bg-navy-900 text-white px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles size={16} className="text-brand-orange" />
              <div>
                <div className="text-sm font-bold">AI સાથી</div>
                <div className="text-[10px] text-white/60">{contextLabel || 'તમારો અભ્યાસ સાથી'}</div>
              </div>
            </div>
            <button onClick={() => setChatOpen(false)} aria-label="બંધ કરો">
              <X size={18} />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-3 space-y-2.5 bg-slate-50">
            {messages.length === 0 && (
              <div className="space-y-2">
                <p className="text-xs text-navy-400 text-center py-2">પ્રશ્ન પૂછો:</p>
                {questions.map((q) => (
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
  )
}
