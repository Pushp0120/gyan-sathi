import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, BookOpenText, Lock, UserRound } from 'lucide-react'
import Logo from '../components/Logo'
import { api } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import type { User } from '../types'

export default function Onboarding() {
  const navigate = useNavigate()
  const { user, updateUser } = useAuth()
  const [fullName, setFullName] = useState(user?.full_name || '')
  const [standard] = useState<number>(10) // GSEB Std 10 only
  const [medium] = useState(user?.medium || 'gujarati') // Gujarati-medium government schools
  const [password, setPassword] = useState('')
  const [passwordMsg, setPasswordMsg] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const submit = async () => {
    if (!fullName.trim()) return
    setBusy(true)
    setError('')
    try {
      const res = await api<{ user: User }>('/api/auth/onboarding', {
        method: 'POST',
        body: JSON.stringify({
          full_name: fullName.trim(),
          standard,
          medium,
          preferred_language: 'gu',
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

  const savePassword = async () => {
    setPasswordMsg('')
    if (password.length < 6) {
      setPasswordMsg('પાસવર્ડ ઓછામાં ઓછો 6 અક્ષરનો હોવો જોઈએ.')
      return
    }
    try {
      await api('/api/auth/set-password', {
        method: 'POST',
        body: JSON.stringify({ password }),
      })
      setPasswordMsg('✓ પાસવર્ડ સેવ થયો — હવે પાસવર્ડથી લોગ ઇન કરી શકાશે.')
    } catch (e: any) {
      setPasswordMsg(e.message)
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

          <div className="rounded-xl bg-navy-50 border border-navy-100 px-4 py-3 flex items-center gap-3">
            <BookOpenText size={20} className="text-brand-blue" />
            <div>
              <div className="text-sm font-bold text-navy-900">ધોરણ 10 — GSEB ગુજરાતી માધ્યમ</div>
              <div className="text-xs text-navy-400">તમામ વિષયો અને પ્રકરણો ગુજરાતીમાં</div>
            </div>
          </div>

          {!user?.has_password && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 space-y-2">
              <label className="text-sm font-medium text-navy-700 flex items-center gap-2">
                <Lock size={15} className="text-brand-orange" /> પાસવર્ડ બનાવો (ભલામણ)
              </label>
              <p className="text-[11px] text-navy-500">
                આગળથી ઈમેલ + પાસવર્ડથી સીધા લોગ ઇન કરી શકાશે — દર વખતે OTP ની જરૂર નહીં.
              </p>
              <div className="flex gap-2">
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="ઓછામાં ઓછા 6 અક્ષર"
                  className="flex-1 rounded-xl border border-amber-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-blue"
                />
                <button
                  onClick={savePassword}
                  className="rounded-xl bg-brand-orange text-white px-4 text-xs font-semibold hover:bg-brand-orange-dark"
                >
                  સેવ કરો
                </button>
              </div>
              {passwordMsg && <div className="text-[11px] text-navy-600">{passwordMsg}</div>}
            </div>
          )}

          <button
            onClick={submit}
            disabled={!fullName.trim() || busy}
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
