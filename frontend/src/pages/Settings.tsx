import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import type { User } from '../types'

export default function Settings() {
  const { user, updateUser, logout } = useAuth()
  const navigate = useNavigate()
  const [fullName, setFullName] = useState(user?.full_name || '')
  const [standard, setStandard] = useState(user?.standard || 10)
  const [medium, setMedium] = useState(user?.medium || 'gujarati')
  const [language, setLanguage] = useState(user?.preferred_language || 'gu')
  const [saved, setSaved] = useState(false)
  const [busy, setBusy] = useState(false)

  const save = async () => {
    setBusy(true)
    try {
      const res = await api<{ user: User }>('/api/auth/onboarding', {
        method: 'POST',
        body: JSON.stringify({
          full_name: fullName,
          standard,
          medium,
          preferred_language: language,
        }),
      })
      updateUser(res.user)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="max-w-md mx-auto px-4 py-6">
      <h1 className="text-lg font-bold text-navy-900 mb-4">સેટિંગ્સ</h1>
      <div className="bg-white rounded-2xl shadow-card p-5 space-y-4">
        <div>
          <label className="text-sm font-medium text-navy-700">નામ</label>
          <input
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="mt-1 w-full rounded-xl border border-navy-100 px-3 py-2.5 text-sm outline-none focus:border-brand-blue"
          />
        </div>
        <div>
          <label className="text-sm font-medium text-navy-700">ધોરણ</label>
          <div className="mt-1 grid grid-cols-2 gap-2">
            {[9, 10].map((s) => (
              <button
                key={s}
                onClick={() => setStandard(s)}
                className={`rounded-xl border-2 py-2.5 text-sm font-bold transition ${
                  standard === s ? 'border-brand-blue bg-navy-50' : 'border-navy-100 text-navy-400'
                }`}
              >
                ધોરણ {s}
              </button>
            ))}
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-sm font-medium text-navy-700">માધ્યમ</label>
            <select
              value={medium}
              onChange={(e) => setMedium(e.target.value)}
              className="mt-1 w-full rounded-xl border border-navy-100 px-3 py-2.5 text-sm bg-white outline-none focus:border-brand-blue"
            >
              <option value="gujarati">ગુજરાતી</option>
              <option value="english">English</option>
            </select>
          </div>
          <div>
            <label className="text-sm font-medium text-navy-700">ભાષા</label>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="mt-1 w-full rounded-xl border border-navy-100 px-3 py-2.5 text-sm bg-white outline-none focus:border-brand-blue"
            >
              <option value="gu">ગુજરાતી</option>
              <option value="en">English</option>
            </select>
          </div>
        </div>
        <button
          onClick={save}
          disabled={busy}
          className="w-full rounded-xl bg-brand-blue text-white py-2.5 text-sm font-semibold hover:bg-navy-800 disabled:opacity-50"
        >
          {busy ? 'સેવ થઈ રહ્યું છે…' : saved ? '✓ સેવ થયું' : 'સેવ કરો'}
        </button>
      </div>
    </div>
  )
}
