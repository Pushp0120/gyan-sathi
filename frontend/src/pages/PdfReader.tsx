import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ChevronLeft, BookOpen, Download } from 'lucide-react'
import { api } from '../services/api'
import type { Subject } from '../types'
import FloatingChat from '../components/FloatingChat'

export default function PdfReader() {
  const { subjectId } = useParams()
  const [subject, setSubject] = useState<Subject | null>(null)
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)

  // Fetch the subject's textbook embed URL (hosted on Google Drive)
  useEffect(() => {
    if (!subjectId) return
    setLoading(true)
    setFailed(false)
    api<{ subject: Subject; pdf_url: string | null; download_url: string | null }>(
      `/api/subjects/${subjectId}/textbook`
    )
      .then((r) => {
        setSubject(r.subject)
        if (r.pdf_url) {
          setPdfUrl(r.pdf_url)
          setDownloadUrl(r.download_url)
        } else setFailed(true)
      })
      .catch(() => setFailed(true))
      .finally(() => setLoading(false))
  }, [subjectId])

  return (
    <div className="h-[calc(100dvh-3.5rem)] flex flex-col">
      {/* Toolbar */}
      <div className="flex items-center gap-2 px-3 py-2 bg-white border-b border-navy-100 shadow-sm z-10">
        <Link
          to={subjectId ? `/subjects/${subjectId}` : '/subjects'}
          className="text-xs text-navy-400 hover:text-navy-700 flex items-center gap-1 shrink-0"
        >
          <ChevronLeft size={14} /> પ્રકરણો
        </Link>
        <div className="min-w-0 flex-1 text-center">
          <div className="text-sm font-bold text-navy-900 truncate">
            📕 {subject?.name_gu || 'પાઠ્યપુસ્તક'} · ધોરણ 10
          </div>
        </div>
        {downloadUrl && (
          <a
            href={downloadUrl}
            download
            target="_blank"
            rel="noreferrer"
            className="p-1.5 rounded-lg hover:bg-slate-100 text-navy-500"
            aria-label="ડાઉનલોડ કરો"
          >
            <Download size={16} />
          </a>
        )}
      </div>

      {/* Content: Google Drive viewer (has its own page navigation & zoom) */}
      <div className="flex-1 bg-slate-200/70">
        {loading && (
          <div className="text-sm text-navy-500 text-center py-20">
            <BookOpen className="inline mr-2" size={18} />
            પાઠ્યપુસ્તક ખોલી રહ્યા છીએ…
          </div>
        )}
        {!loading && failed && (
          <div className="bg-white rounded-2xl shadow-card p-8 text-center max-w-md mx-auto mt-8">
            <div className="text-3xl">📕</div>
            <div className="mt-2 font-bold text-navy-900">પાઠ્યપુસ્તક મળ્યું નથી</div>
            <p className="text-xs text-navy-400 mt-1">આ વિષય માટે પાઠ્યપુસ્તક ટૂંક સમયમાં ઉમેરાશે.</p>
          </div>
        )}
        {!loading && !failed && pdfUrl && (
          <iframe
            src={pdfUrl}
            title={subject?.name_gu || 'પાઠ્યપુસ્તક'}
            className="w-full h-full border-0"
            allow="autoplay"
          />
        )}
      </div>

      <FloatingChat
        contextLabel={subject?.name_gu ? `પાઠ્યપુસ્તક · ${subject.name_gu}` : 'પાઠ્યપુસ્તક'}
        subjectId={subjectId || null}
        quickQuestions={[
          'આ વિષયમાં કયા પ્રકરણ છે?',
          'મહત્વના પ્રશ્નો બતાવો',
          'પરીક્ષામાં શું પૂછાય છે?',
        ]}
      />
    </div>
  )
}
