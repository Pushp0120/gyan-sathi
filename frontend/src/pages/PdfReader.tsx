import { useCallback, useEffect, useRef, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import * as pdfjsLib from 'pdfjs-dist'
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
import { ChevronLeft, ChevronRight, Download, ZoomIn, ZoomOut, BookOpen } from 'lucide-react'
import { api } from '../services/api'
import type { Subject } from '../types'
import FloatingChat from '../components/FloatingChat'

pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl

interface PageInfo {
  page: pdfjsLib.PDFPageProxy | null
  error?: boolean
}

export default function PdfReader() {
  const { subjectId } = useParams()
  const [subject, setSubject] = useState<Subject | null>(null)
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [doc, setDoc] = useState<pdfjsLib.PDFDocumentProxy | null>(null)
  const [numPages, setNumPages] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [scale, setScale] = useState(1.15)
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)
  const [pages, setPages] = useState<PageInfo[]>([])
  const containerRef = useRef<HTMLDivElement>(null)
  const pageRefs = useRef<(HTMLDivElement | null)[]>([])

  // Fetch the subject's textbook URL
  useEffect(() => {
    if (!subjectId) return
    setLoading(true)
    setFailed(false)
    setDoc(null)
    setPages([])
    api<{ subject: Subject; pdf_url: string | null }>(`/api/subjects/${subjectId}/textbook`)
      .then((r) => {
        setSubject(r.subject)
        if (r.pdf_url) setPdfUrl(r.pdf_url)
        else setFailed(true)
      })
      .catch(() => setFailed(true))
  }, [subjectId])

  // Load the PDF document
  useEffect(() => {
    if (!pdfUrl) return
    let cancelled = false
    const task = pdfjsLib.getDocument({ url: pdfUrl })
    task.promise
      .then((d) => {
        if (cancelled) return
        setDoc(d)
        setNumPages(d.numPages)
        setPages(Array.from({ length: d.numPages }, () => ({ page: null })))
      })
      .catch(() => {
        if (!cancelled) setFailed(true)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
      task.destroy()
    }
  }, [pdfUrl])

  // Render pages on demand
  const renderPage = useCallback(
    async (pdf: pdfjsLib.PDFDocumentProxy, pageNum: number, s: number) => {
      const holder = pageRefs.current[pageNum - 1]
      if (!holder) return
      if (holder.dataset.renderedScale === String(s)) return
      try {
        const page = await pdf.getPage(pageNum)
        const dpr = Math.min(window.devicePixelRatio || 1, 2)
        const viewport = page.getViewport({ scale: s * dpr })
        const cssVp = page.getViewport({ scale: s })
        holder.innerHTML = ''
        const canvas = document.createElement('canvas')
        canvas.width = viewport.width
        canvas.height = viewport.height
        canvas.style.width = `${cssVp.width}px`
        canvas.style.height = `${cssVp.height}px`
        holder.dataset.renderedScale = String(s)
        holder.appendChild(canvas)
        await page.render({ canvasContext: canvas.getContext('2d')!, viewport }).promise
        setPages((ps) => ps.map((p, i) => (i === pageNum - 1 ? { page } : p)))
      } catch {
        holder.dataset.renderedScale = ''
      }
    },
    []
  )

  useEffect(() => {
    if (!doc || !numPages) return
    const w = 2 // render current page ± 2 for smooth scroll
    for (let n = Math.max(1, currentPage - w); n <= Math.min(numPages, currentPage + w); n++) {
      void renderPage(doc, n, scale)
    }
  }, [doc, numPages, currentPage, scale, renderPage])

  // Track visible page while scrolling
  useEffect(() => {
    const el = containerRef.current
    if (!el || !numPages) return
    const onScroll = () => {
      const mid = el.scrollTop + el.clientHeight / 3
      for (let i = 0; i < pageRefs.current.length; i++) {
        const h = pageRefs.current[i]
        if (!h) continue
        if (h.offsetTop <= mid && h.offsetTop + h.offsetHeight >= mid) {
          setCurrentPage((c) => (c === i + 1 ? c : i + 1))
          break
        }
      }
    }
    el.addEventListener('scroll', onScroll, { passive: true })
    return () => el.removeEventListener('scroll', onScroll)
  }, [numPages])

  const goto = (n: number) => {
    const clamped = Math.max(1, Math.min(numPages || 1, n))
    setCurrentPage(clamped)
    pageRefs.current[clamped - 1]?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

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
          {numPages > 0 && (
            <div className="text-[10px] text-navy-400">
              પાનું {currentPage} / {numPages}
            </div>
          )}
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <button
            onClick={() => goto(currentPage - 1)}
            disabled={currentPage <= 1}
            className="p-1.5 rounded-lg hover:bg-slate-100 disabled:opacity-30"
            aria-label="પાછળા પાનું"
          >
            <ChevronLeft size={16} />
          </button>
          <button
            onClick={() => goto(currentPage + 1)}
            disabled={currentPage >= numPages}
            className="p-1.5 rounded-lg hover:bg-slate-100 disabled:opacity-30"
            aria-label="આગળનું પાનું"
          >
            <ChevronRight size={16} />
          </button>
          <button
            onClick={() => setScale((s) => Math.max(0.6, +(s - 0.15).toFixed(2)))}
            className="p-1.5 rounded-lg hover:bg-slate-100"
            aria-label="નાનું કરો"
          >
            <ZoomOut size={16} />
          </button>
          <button
            onClick={() => setScale((s) => Math.min(2.5, +(s + 0.15).toFixed(2)))}
            className="p-1.5 rounded-lg hover:bg-slate-100"
            aria-label="મોટું કરો"
          >
            <ZoomIn size={16} />
          </button>
          {pdfUrl && (
            <a
              href={pdfUrl}
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
      </div>

      {/* Pages */}
      <div ref={containerRef} className="flex-1 overflow-y-auto bg-slate-200/70 px-3 py-4">
        {loading && (
          <div className="text-sm text-navy-500 text-center py-20">
            <BookOpen className="inline mr-2" size={18} />
            પાઠ્યપુસ્તક ખોલી રહ્યા છીએ…
          </div>
        )}
        {failed && (
          <div className="bg-white rounded-2xl shadow-card p-8 text-center max-w-md mx-auto">
            <div className="text-3xl">📕</div>
            <div className="mt-2 font-bold text-navy-900">પાઠ્યપુસ્તક મળ્યું નથી</div>
            <p className="text-xs text-navy-400 mt-1">આ વિષય માટે પાઠ્યપુસ્તક ટૂંક સમયમાં ઉમેરાશે.</p>
          </div>
        )}
        {doc &&
          pages.map((_, i) => (
            <div
              key={i}
              ref={(el) => {
                pageRefs.current[i] = el
              }}
              className="mx-auto mb-4 bg-white shadow-lg rounded overflow-hidden w-fit min-w-[min(90vw,700px)] min-h-[120px]"
              data-page={i + 1}
            >
              <div className="px-2 py-1 text-[10px] text-navy-300 text-center">{i + 1}</div>
            </div>
          ))}
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
