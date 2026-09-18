import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../services/api'
import type { Chapter, Subject } from '../types'
import FloatingChat from '../components/FloatingChat'

interface ReaderSection {
  section: string
  heading?: string
  order: number
}

/** Very small markdown subset renderer: **bold**, *italic*, headings, list items. */
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
  const [chapter, setChapter] = useState<Chapter | null>(null)
  const [subject, setSubject] = useState<Subject | null>(null)
  const [sections, setSections] = useState<ReaderSection[]>([])
  const [loading, setLoading] = useState(true)
  const [notReady, setNotReady] = useState(false)

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

      <FloatingChat
        contextLabel={chapter ? `પ્રકરણ ${chapter.number} · ${chapter.name_gu}` : 'તમારો અભ્યાસ સાથી'}
        subjectId={subject?.id || null}
        chapterId={chapterId || null}
        quickQuestions={quickQuestions}
      />
    </div>
  )
}
