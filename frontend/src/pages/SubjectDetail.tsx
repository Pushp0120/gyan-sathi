import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'
import { api } from '../services/api'
import type { Chapter, Subject } from '../types'

export default function SubjectDetail() {
  const { subjectId } = useParams()
  const [subject, setSubject] = useState<Subject | null>(null)
  const [chapters, setChapters] = useState<Chapter[]>([])

  useEffect(() => {
    if (subjectId) {
      api<{ subject: Subject; chapters: Chapter[] }>(`/api/subjects/${subjectId}/chapters`)
        .then((r) => {
          setSubject(r.subject)
          setChapters(r.chapters)
        })
        .catch(() => {})
    }
  }, [subjectId])

  return (
    <div className="max-w-3xl mx-auto px-4 py-6">
      <div className="flex items-center gap-3 mb-5">
        <span className="text-4xl">{subject?.icon}</span>
        <div>
          <h1 className="text-lg font-bold text-navy-900">{subject?.name_gu}</h1>
          <p className="text-xs text-navy-400">
            ધોરણ {subject?.standard} · {subject?.name_en}
          </p>
        </div>
      </div>
      <div className="space-y-2">
        {chapters.map((c, i) => (
          <Link
            key={c.id}
            to={`/read/${c.id}`}
            className="chapter-roll chapter-book flex items-center gap-3 rounded-2xl shadow-card px-4 py-3.5 hover:shadow-card-hover hover:-translate-y-0.5 transition"
            style={{ ['--roll-delay' as string]: `${i * 70}ms` }}
          >
            <span className="w-8 h-8 rounded-full bg-navy-900 text-white text-sm font-bold flex items-center justify-center shrink-0">
              {c.number}
            </span>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold text-navy-900 truncate">{c.name_gu}</div>
              {c.name_en && <div className="text-[11px] text-navy-400 truncate">{c.name_en}</div>}
            </div>
            <ChevronRight size={17} className="text-navy-300" />
          </Link>
        ))}
        {chapters.length === 0 && (
          <div className="text-sm text-navy-400 bg-white rounded-2xl p-6 text-center shadow-card">
            પ્રકરણો ટૂંક સમયમાં ઉમેરશે.
          </div>
        )}
      </div>
    </div>
  )
}
