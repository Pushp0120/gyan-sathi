import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, BookOpenText, Globe, UserRound } from 'lucide-react'
import Logo from '../components/Logo'
import { api } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import type { User } from '../types'

export default function Onboarding() {
  const navigate = useNavigate()
  const { user, updateUser } = useAuth()
  const [fullName, setFullName] = useState(user?.full_name || '')
  const [standard, setStandard] = useState<number | null>(user?.standard || null)
  const [medium, setMedium] = useState(user?.medium || 'gujarati')
  const [language, setLanguage] = useState(user?.preferred_language || 'gu')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const submit = async () => {
    if (!fullName.trim() || !standard) return
    setBusy(true)
    setError('')
    try {
      const res = await api<{ user: User }>('/api/auth/onboarding', {
        method: 'POST',
        body: JSON.stringify({
          full_name: fullName.trim(),
          standard,
          medium,
          preferred_language: language,
        }),
      })
      updateUser(res.user)
      navigate('/dashboard')
    } catch (e: any) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-full flex flex-col items-center justify-center px-4 py-10 bg-gradient-to-b from-navy-50 to-white">
      <div className="w-full max-w-md">
        <div className="flex flex-col items-center mb-6">
          <Logo size={72} withText={false} />
          <h1 className="mt-3 text-xl font-extrabold text-navy-900">
            Gyan Sathi માં આપનું સ્વાગત છે 👋
          </h1>
          <p className="text-sm text-navy-500 mt-1">ચાલો તમારું પ્રોફાઇલ સેટ કરીએ</p>
        </div>

        <div className="bg-white rounded-2xl shadow-card p-6 space-y-5">
          <div>
            <label className="text-sm font-medium text-navy-700 flex items-center gap-2">
              <UserRound size={16} className="text-brand-orange" /> તમારું નામ
            </label>
            <input
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="તમારું નામ લખો"
              className="mt-1 w-full rounded-xl border border-navy-100 px-3 py-2.5 text-sm outline-none focus:border-brand-blue"
            />
          </div>

          <div>
            <label className="text-sm font-medium text-navy-700 flex items-center gap-2">
              <BookOpenText size={16} className="text-brand-orange" /> ધોરણ પસંદ કરો
            </label>
            <div className="mt-2 grid grid-cols-2 gap-3">
              {[9, 10].map((s) => (
                <button
                  key={s}
                  onClick={() => setStandard(s)}
                  className={`rounded-2xl border-2 py-4 text-center transition ${
                    standard === s
                      ? 'border-brand-blue bg-navy-50 shadow-card'
                      : 'border-navy-100 hover:border-navy-200'
                  }`}
                >
                  <div className="text-2xl font-extrabold text-navy-900">ધોરણ {s}</div>
                  <div className="text-xs text-navy-400 mt-1">Std. {s}</div>
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-navy-700">માધ્યમ</label>
              <select
                value={medium}
                onChange={(e) => setMedium(e.target.value)}
                className="mt-1 w-full rounded-xl border border-navy-100 px-3 py-2.5 text-sm outline-none focus:border-brand-blue bg-white"
              >
                <option value="gujarati">ગુજરાતી</option>
                <option value="english">English</option>
              </select>
            </div>
            <div>
              <label className="text-sm font-medium text-navy-700 flex items-center gap-1">
                <Globe size={14} className="text-brand-orange" /> ભાષા
              </label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="mt-1 w-full rounded-xl border border-navy-100 px-3 py-2.5 text-sm outline-none focus:border-brand-blue bg-white"
              >
                <option value="gu">ગુજરાતી</option>
                <option value="en">English</option>
              </select>
            </div>
          </div>

          <button
            onClick={submit}
            disabled={!fullName.trim() || !standard || busy}
            className="w-full flex items-center justify-center gap-2 rounded-xl bg-brand-blue text-white py-3 text-sm font-semibold hover:bg-navy-800 disabled:opacity-50"
          >
            {busy ? 'સેટ થઈ રહ્યું છે…' : <>શરૂ કરો <ArrowRight size={16} /></>}
          </button>
          {error && <div className="rounded-xl bg-red-50 text-red-600 text-xs px-3 py-2">{error}</div>}
        </div>
      </div>
    </div>
  )
}
