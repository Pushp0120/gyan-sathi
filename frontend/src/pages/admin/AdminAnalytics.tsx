import { useEffect, useState } from 'react'
import { ThumbsDown, ThumbsUp } from 'lucide-react'
import { api } from '../../services/api'

export default function AdminAnalytics() {
  const [feedback, setFeedback] = useState<any[]>([])
  const [questions, setQuestions] = useState<any[]>([])

  useEffect(() => {
    api<{ feedback: any[] }>('/api/admin/feedback').then((r) => setFeedback(r.feedback)).catch(() => {})
    api<{ questions: any[] }>('/api/admin/quiz-questions')
      .then((r) => setQuestions(r.questions))
      .catch(() => {})
  }, [])

  return (
    <div className="p-4 md:p-6 space-y-6">
      <h1 className="text-lg font-bold text-navy-900">વિશ્લેષણ અને પ્રતિસાદ</h1>

      <section>
        <h2 className="font-semibold text-navy-800 mb-2">વિદ્યાર્થી પ્રતિસાદ ({feedback.length})</h2>
        <div className="space-y-2">
          {feedback.map((f) => (
            <div key={f.id} className="bg-white rounded-2xl shadow-card p-3.5">
              <div className="flex items-center gap-2">
                {f.rating === 'up' ? (
                  <ThumbsUp size={14} className="text-brand-green" />
                ) : (
                  <ThumbsDown size={14} className="text-red-500" />
                )}
                <span className="text-xs font-semibold text-navy-700">{f.student_email}</span>
                <span className="ml-auto text-[11px] text-navy-300">
                  {f.created_at ? new Date(f.created_at).toLocaleString('gu-IN') : ''}
                </span>
              </div>
              <div className="mt-1.5 text-xs text-navy-500 bg-navy-50 rounded-lg px-3 py-2">
                {f.message_preview}
              </div>
              {f.comment && <div className="mt-1 text-xs text-navy-600">💬 {f.comment}</div>}
            </div>
          ))}
          {feedback.length === 0 && (
            <div className="text-center text-sm text-navy-400 bg-white rounded-2xl p-6 shadow-card">
              હજી પ્રતિસાદ નથી.
            </div>
          )}
        </div>
      </section>

      <section>
        <h2 className="font-semibold text-navy-800 mb-2">AI જનરેટ કરેલા ક્વિઝ પ્રશ્નો ({questions.length})</h2>
        <div className="bg-white rounded-2xl shadow-card divide-y divide-navy-50 max-h-96 overflow-y-auto">
          {questions.slice(0, 30).map((q) => (
            <div key={q.id} className="px-4 py-3">
              <div className="text-sm text-navy-900">{q.question_text}</div>
              <div className="text-xs text-brand-green mt-0.5">✓ {q.correct_answer}</div>
              <div className="text-[11px] text-navy-300">
                ધોરણ {q.standard} · {q.difficulty}
              </div>
            </div>
          ))}
          {questions.length === 0 && (
            <div className="text-center text-sm text-navy-400 py-6">હજી પ્રશ્નો જનરેટ થયા નથી.</div>
          )}
        </div>
      </section>
    </div>
  )
}
