import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Eye, EyeOff, Lock, Mail } from 'lucide-react'
import Logo from '../components/Logo'
import { api } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import type { User } from '../types'

export default function Signup() {
  const navigate = useNavigate()
  const { loginWithToken } = useAuth()
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const signup = async () => {
    setError('')
    if (!fullName.trim()) {
      setError('તમારું નામ લખો.')
      return
    }
    if (password.length < 6) {
      setError('પાસવર્ડ ઓછામાં ઓછો 6 અક્ષરનો હોવો જોઈએ.')
      return
    }
    setBusy(true)
    try {
      const res = await api<{ access_token: string; user: User; needs_onboarding: boolean }>(
        '/api/auth/signup',
        {
          method: 'POST',
          body: JSON.stringify({ email, password, full_name: fullName }),
        }
      )
      loginWithToken(res.access_token, res.user)
      navigate(res.needs_onboarding ? '/onboarding' : '/dashboard')
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
          <Logo size={110} withText={false} />
        </div>

        <div className="bg-white rounded-2xl shadow-card p-6 space-y-4">
          <div className="flex items-center gap-2 text-sm text-navy-600 bg-navy-50 rounded-xl px-3 py-2">
            🎓 ધોરણ 10 ના વિદ્યાર્થીઓ માટે — સંપૂર્ણ મફત શરૂઆત
          </div>
          <div>
            <label className="text-sm font-medium text-navy-700">તમારું નામ</label>
            <input
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="તમારું નામ"
              className="mt-1 w-full rounded-xl border border-navy-100 px-3 py-2.5 text-sm outline-none focus:border-brand-blue"
            />
          </div>
          <div>
            <label className="text-sm font-medium text-navy-700">ઈમેલ</label>
            <div className="mt-1 flex items-center rounded-xl border border-navy-100 px-3 focus-within:border-brand-blue">
              <Mail size={18} className="text-navy-300" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="tamaru@email.com"
                className="w-full bg-transparent px-2 py-2.5 text-sm outline-none"
              />
            </div>
          </div>
          <div>
            <label className="text-sm font-medium text-navy-700">પાસવર્ડ બનાવો</label>
            <div className="mt-1 flex items-center rounded-xl border border-navy-100 px-3 focus-within:border-brand-blue">
              <Lock size={18} className="text-navy-300" />
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && email && password && signup()}
                placeholder="ઓછામાં ઓછા 6 અક્ષર"
                className="w-full bg-transparent px-2 py-2.5 text-sm outline-none"
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                aria-label={showPassword ? 'પાસવર્ડ છુપાવો' : 'પાસવર્ડ બતાવો'}
                className="p-1 text-navy-400 hover:text-navy-700"
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
            <p className="mt-1 text-[11px] text-navy-400">
              આ પાસવર્ડથી સીધા લોગ ઇન કરશો — કોઈ OTP જરૂરી નથી.
            </p>
          </div>
          <button
            onClick={signup}
            disabled={!email || !password || busy}
            className="w-full rounded-xl bg-brand-orange text-white py-2.5 text-sm font-semibold hover:bg-brand-orange-dark disabled:opacity-50"
          >
            {busy ? 'ખાતું બની રહ્યું છે…' : 'ખાતું બનાવો ✓'}
          </button>
          <div className="text-center text-sm text-navy-500">
            પહેલેથી ખાતું છે?{' '}
            <Link to="/login" className="text-base font-bold text-brand-blue">
              લોગ ઇન
            </Link>
          </div>
          {error && <div className="rounded-xl bg-red-50 text-red-600 text-xs px-3 py-2">{error}</div>}
        </div>
      </div>
    </div>
  )
}
