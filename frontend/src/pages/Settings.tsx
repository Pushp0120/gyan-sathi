import { useState } from 'react'
import { api } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import type { User } from '../types'

export default function Settings() {
  const { user, updateUser } = useAuth()
  const [fullName, setFullName] = useState(user?.full_name || '')
  const [password, setPassword] = useState('')
  const [saved, setSaved] = useState(false)
  const [pwMsg, setPwMsg] = useState('')
  const [busy, setBusy] = useState(false)

  const save = async () => {
    setBusy(true)
    try {
      const res = await api<{ user: User }>('/api/auth/onboarding', {
        method: 'POST',
        body: JSON.stringify({
          full_name: fullName,
          standard: 10,
          medium: 'gujarati',
          preferred_language: 'gu',
        }),
      })
      updateUser(res.user)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } finally {
      setBusy(false)
    }
  }

  const savePassword = async () => {
    setPwMsg('')
    if (password.length < 6) {
      setPwMsg('પાસવર્ડ ઓછામાં ઓછો 6 અક્ષરનો હોવો જોઈએ.')
      return
    }
    try {
      await api('/api/auth/set-password', {
        method: 'POST',
        body: JSON.stringify({ password }),
      })
      setPassword('')
      setPwMsg('✓ પાસવર્ડ સેવ થયો')
      updateUser({ has_password: true })
    } catch (e: any) {
      setPwMsg(e.message)
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
        <div className="rounded-xl bg-navy-50 border border-navy-100 px-4 py-3 text-sm">
          <span className="font-bold text-navy-900">ધોરણ 10</span>
          <span className="text-navy-400"> · GSEB ગુજરાતી માધ્યમ</span>
        </div>
        <button
          onClick={save}
          disabled={busy}
          className="w-full rounded-xl bg-brand-blue text-white py-2.5 text-sm font-semibold hover:bg-navy-800 disabled:opacity-50"
        >
          {busy ? 'સેવ થઈ રહ્યું છે…' : saved ? '✓ સેવ થયું' : 'સેવ કરો'}
        </button>
      </div>

      <div className="bg-white rounded-2xl shadow-card p-5 space-y-3 mt-4">
        <label className="text-sm font-medium text-navy-700">
          {user?.has_password ? 'પાસવર્ડ બદલો' : 'પાસવર્ડ બનાવો'}
        </label>
        {!user?.has_password && (
          <p className="text-[11px] text-navy-400">
            પાસવર્ડ સેવ કરો એટલે આગળથી OTP વગર સીધા લોગ ઇન કરી શકાશે.
          </p>
        )}
        <div className="flex gap-2">
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="ઓછામાં ઓછા 6 અક્ષર"
            className="flex-1 rounded-xl border border-navy-100 px-3 py-2.5 text-sm outline-none focus:border-brand-blue"
          />
          <button
            onClick={savePassword}
            className="rounded-xl bg-navy-900 text-white px-4 text-sm font-semibold hover:bg-navy-800"
          >
            સેવ કરો
          </button>
        </div>
        {pwMsg && <div className="text-xs text-navy-600">{pwMsg}</div>}
      </div>
    </div>
  )
}
