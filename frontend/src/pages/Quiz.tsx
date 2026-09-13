import { useEffect, useState } from 'react'
import { Brain, CheckCircle2, ChevronRight, RotateCcw, XCircle } from 'lucide-react'
import { api } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import type { Chapter, QuizQuestion, Subject } from '../types'

type Stage = 'setup' | 'playing' | 'result'

interface Result {
  total: number
  correct: number
  wrong: number
  score_percent: number
  details: { question_index: number; selected: string; correct: string; is_right: boolean }[]
}

export default function Quiz() {
  const { user } = useAuth()
  const [stage, setStage] = useState<Stage>('setup')
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [subjectId, setSubjectId] = useState('')
  const [chapters, setChapters] = useState<Chapter[]>([])
  const [chapterId, setChapterId] = useState('')
  const [count, setCount] = useState(5)
  const [questions, setQuestions] = useState<QuizQuestion[]>([])
  const [current, setCurrent] = useState(0)
  const [answers, setAnswers] = useState<{ question_index: number; selected: string }[]>([])
  const [selected, setSelected] = useState('')
  const [result, setResult] = useState<Result | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api<{ subjects: Subject[] }>(`/api/subjects?standard=${user?.standard}`)
      .then((r) => setSubjects(r.subjects))
      .catch(() => {})
  }, [user?.standard])

  useEffect(() => {
    if (!subjectId) return setChapters([])
    api<{ chapters: Chapter[] }>(`/api/subjects/${subjectId}/chapters`)
      .then((r) => setChapters(r.chapters))
      .catch(() => {})
  }, [subjectId])

  const start = async () => {
    if (!subjectId) return
    setBusy(true)
    setError('')
    try {
      const res = await api<{ questions: QuizQuestion[] }>('/api/quiz/generate', {
        method: 'POST',
        body: JSON.stringify({ standard: user?.standard, subject_id: subjectId, chapter_id: chapterId || null, count }),
      })
      setQuestions(res.questions)
      setCurrent(0)
      setAnswers([])
      setSelected('')
      setStage('playing')
    } catch (e: any) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  const next = async () => {
    const newAnswers = [...answers, { question_index: current, selected }]
    setAnswers(newAnswers)
    setSelected('')
    if (current + 1 < questions.length) {
      setCurrent(current + 1)
    } else {
      setBusy(true)
      try {
        const payload = newAnswers.map((a) => ({
          question_id: questions[a.question_index]?.id,
          question_index: a.question_index,
          selected: a.selected,
          subject_id: subjectId,
          chapter_id: chapterId || null,
        }))
        const res = await api<Result>(`/api/quiz/submit`, {
          method: 'POST',
          body: JSON.stringify({ answers: payload }),
        })
        setResult(res)
        setStage('result')
      } catch (e: any) {
        setError(e.message)
      } finally {
        setBusy(false)
      }
    }
  }

  if (stage === 'setup') {
    return (
      <div className="max-w-md mx-auto px-4 py-8">
        <div className="bg-white rounded-2xl shadow-card p-6 space-y-4">
          <div className="text-center">
            <Brain className="mx-auto text-brand-orange" size={36} />
            <h1 className="text-lg font-bold text-navy-900 mt-2">ક્વિઝ રમો 🧠</h1>
            <p className="text-xs text-navy-500 mt-1">AI તમારા અભ્યાસક્રમ પરથી પ્રશ્નો બનાવશે</p>
          </div>
          <div>
            <label className="text-sm font-medium text-navy-700">વિષય</label>
            <select
              value={subjectId}
              onChange={(e) => setSubjectId(e.target.value)}
              className="mt-1 w-full rounded-xl border border-navy-100 px-3 py-2.5 text-sm bg-white outline-none focus:border-brand-blue"
            >
              <option value="">— વિષય પસંદ કરો —</option>
              {subjects.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.icon} {s.name_gu}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-sm font-medium text-navy-700">પ્રકરણ (વૈકલ્પિક)</label>
            <select
              value={chapterId}
              onChange={(e) => setChapterId(e.target.value)}
              disabled={!chapters.length}
              className="mt-1 w-full rounded-xl border border-navy-100 px-3 py-2.5 text-sm bg-white outline-none focus:border-brand-blue disabled:opacity-50"
            >
              <option value="">આખો વિષય</option>
              {chapters.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.number}. {c.name_gu}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-sm font-medium text-navy-700">પ્રશ્નોની સંખ્યા</label>
            <div className="mt-1 grid grid-cols-3 gap-2">
              {[5, 10, 20].map((n) => (
                <button
                  key={n}
                  onClick={() => setCount(n)}
                  className={`rounded-xl border-2 py-2.5 text-sm font-bold transition ${
                    count === n ? 'border-brand-blue bg-navy-50 text-navy-900' : 'border-navy-100 text-navy-400'
                  }`}
                >
                  {n}
                </button>
              ))}
            </div>
          </div>
          <button
            onClick={start}
            disabled={!subjectId || busy}
            className="w-full rounded-xl bg-brand-orange text-white py-3 text-sm font-bold hover:bg-brand-orange-dark disabled:opacity-50"
          >
            {busy ? 'પ્રશ્નો બને છે… ⏳' : 'ક્વિઝ શરૂ કરો'}
          </button>
          {error && <div className="rounded-xl bg-red-50 text-red-600 text-xs px-3 py-2">{error}</div>}
        </div>
      </div>
    )
  }

  if (stage === 'playing' && questions.length > 0) {
    const q = questions[current]
    return (
      <div className="max-w-xl mx-auto px-4 py-6">
        <div className="flex items-center justify-between mb-3">
          <div className="text-xs font-semibold text-navy-500">
            પ્રશ્ન {current + 1} / {questions.length}
          </div>
          <div className="h-2 flex-1 mx-3 rounded-full bg-navy-100 overflow-hidden">
            <div
              className="h-full bg-brand-orange rounded-full transition-all"
              style={{ width: `${((current + 1) / questions.length) * 100}%` }}
            />
          </div>
        </div>
        <div className="bg-white rounded-2xl shadow-card p-5 space-y-4">
          <div className="text-sm font-semibold text-navy-900 leading-relaxed">{q.question}</div>
          <div className="space-y-2">
            {q.options.map((opt, i) => (
              <button
                key={i}
                onClick={() => setSelected(opt)}
                className={`w-full text-left rounded-xl border-2 px-4 py-3 text-sm transition ${
                  selected === opt
                    ? 'border-brand-blue bg-navy-50 font-semibold'
                    : 'border-navy-100 hover:border-navy-200'
                }`}
              >
                <span className="inline-flex w-6 h-6 rounded-full bg-navy-50 items-center justify-center text-xs font-bold text-navy-600 mr-2">
                  {['ક', 'ખ', 'ગ', 'ઘ'][i]}
                </span>
                {opt}
              </button>
            ))}
          </div>
          <button
            onClick={next}
            disabled={!selected || busy}
            className="w-full flex items-center justify-center gap-1 rounded-xl bg-brand-blue text-white py-2.5 text-sm font-semibold disabled:opacity-40"
          >
            {current + 1 === questions.length ? 'સબમિટ કરો' : 'આગળ'} <ChevronRight size={16} />
          </button>
        </div>
      </div>
    )
  }

  if (stage === 'result' && result) {
    const emoji = result.score_percent >= 80 ? '🎉' : result.score_percent >= 50 ? '👍' : '💪'
    return (
      <div className="max-w-xl mx-auto px-4 py-6 space-y-4">
        <div className="bg-white rounded-2xl shadow-card p-6 text-center">
          <div className="text-4xl">{emoji}</div>
          <div className="mt-2 text-3xl font-extrabold text-navy-900">
            {result.correct}/{result.total}
          </div>
          <div className="text-sm text-navy-500 mt-1">
            સ્કોર: {result.score_percent}% · સાચા: {result.correct} · ખોટા: {result.wrong}
          </div>
          <button
            onClick={() => setStage('setup')}
            className="mt-4 inline-flex items-center gap-1.5 rounded-xl bg-brand-blue text-white px-4 py-2 text-sm font-semibold"
          >
            <RotateCcw size={15} /> ફરી રમો
          </button>
        </div>
        <div className="space-y-3">
          <h2 className="font-bold text-navy-900">સમજૂતી સાથે સમીક્ષા</h2>
          {result.details.map((d, i) => {
            const q = questions[d.question_index]
            if (!q) return null
            return (
              <div key={i} className="bg-white rounded-2xl shadow-card p-4 space-y-2">
                <div className="flex items-start gap-2">
                  {d.is_right ? (
                    <CheckCircle2 size={18} className="text-brand-green shrink-0 mt-0.5" />
                  ) : (
                    <XCircle size={18} className="text-red-500 shrink-0 mt-0.5" />
                  )}
                  <div className="text-sm font-medium text-navy-900">{q.question}</div>
                </div>
                <div className="text-xs text-navy-500 ml-6">
                  તમારો જવાબ: <b className={d.is_right ? 'text-brand-green' : 'text-red-500'}>{d.selected || '—'}</b>
                  {!d.is_right && (
                    <>
                      {' '}· સાચો જવાબ: <b className="text-brand-green">{d.correct}</b>
                    </>
                  )}
                </div>
                {q.explanation && (
                  <div className="ml-6 rounded-xl bg-navy-50 px-3 py-2 text-xs text-navy-700">
                    💡 {q.explanation}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  return null
}
