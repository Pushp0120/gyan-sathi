import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Eye, EyeOff, KeyRound, Lock, Mail, ShieldCheck, Timer, UserRound } from 'lucide-react'
import Logo from '../components/Logo'
import { api } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import type { User } from '../types'

const OTP_VALIDITY_SEC = 300 // 5 minutes (matches backend OTP_EXPIRE_MINUTES)

type Mode = 'password' | 'admin' | 'forgot'

export default function Login() {
  const navigate = useNavigate()
  const { loginWithToken } = useAuth()
  const [mode, setMode] = useState<Mode>('password')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [otpSent, setOtpSent] = useState(false)
  const [otp, setOtp] = useState('')
  const [devMode, setDevMode] = useState(false)
  const [resetDone, setResetDone] = useState(false)
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')
  const [busy, setBusy] = useState(false)
  const [secondsLeft, setSecondsLeft] = useState(0)
  const [resendIn, setResendIn] = useState(0)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    timerRef.current = setInterval(() => {
      setSecondsLeft((s) => (s > 0 ? s - 1 : 0))
      setResendIn((s) => (s > 0 ? s - 1 : 0))
    }, 1000)
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [])

  const switchMode = (m: Mode) => {
    setMode(m)
    setError('')
    setInfo('')
    setOtpSent(false)
    setResetDone(false)
    setOtp('')
    setPassword('')
    setShowPassword(false)
  }

  const sendOtp = async () => {
    setError('')
    setInfo('')
    setBusy(true)
    try {
      const res = await api<{ sent: boolean; dev_mode?: boolean; message?: string }>(
        '/api/auth/send-otp',
        { method: 'POST', body: JSON.stringify({ email }) }
      )
      setOtpSent(true)
      setSecondsLeft(OTP_VALIDITY_SEC)
      setResendIn(30)
      setOtp('')
      if (res.dev_mode) {
        setDevMode(true)
        setInfo('Dev mode: OTP "000000" વાપરો (SMTP સેટ નથી).')
      } else {
        setInfo('તમારા ઈમેલ પર OTP મોકલવામાં આવ્યો છે. તપાસો 📩')
      }
    } catch (e: any) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  const verifyOtp = async () => {
    setError('')
    setBusy(true)
    try {
      // Recovery flow: correct OTP → issue token → student sets a new password
      const res = await api<{ access_token: string; user: User; needs_onboarding: boolean }>(
        '/api/auth/verify-otp',
        { method: 'POST', body: JSON.stringify({ email, otp }) }
      )
      loginWithToken(res.access_token, res.user)
      setResetDone(true)
      setOtpSent(false)
      setInfo('')
      setError('')
    } catch (e: any) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  const saveNewPassword = async () => {
    setError('')
    if (password.length < 6) {
      setError('પાસવર્ડ ઓછામાં ઓછો 6 અક્ષરનો હોવો જોઈએ.')
      return
    }
    setBusy(true)
    try {
      await api('/api/auth/set-password', {
        method: 'POST',
        body: JSON.stringify({ password }),
      })
      navigate('/dashboard')
    } catch (e: any) {
      setError(e.message)
      setBusy(false)
    }
  }

  const loginPassword = async () => {
    setError('')
    setBusy(true)
    try {
      const res = await api<{ access_token: string; user: User; needs_onboarding: boolean }>(
        '/api/auth/login',
        { method: 'POST', body: JSON.stringify({ email, password }) }
      )
      loginWithToken(res.access_token, res.user)
      navigate(res.user.role === 'admin' ? '/admin' : res.needs_onboarding ? '/onboarding' : '/dashboard')
    } catch (e: any) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-full flex flex-col items-center justify-center px-4 py-10 bg-gradient-to-b from-navy-50 to-white">
      <div className="w-full max-w-md">
        <div className="flex flex-col items-center mb-8">
          <Logo size={96} withText={false} />
          <h1 className="mt-3 text-2xl font-extrabold text-navy-900">
            Gyan <span className="text-brand-orange">Sathi</span>
          </h1>
          <p className="text-sm text-navy-500 mt-1">તમારો અભ્યાસ, અમારો સાથી</p>
        </div>

        <div className="bg-white rounded-2xl shadow-card p-6 space-y-4">
          {mode === 'password' && !resetDone && (
            <div className="space-y-3">
              <div className="text-center">
                <UserRound className="mx-auto text-brand-blue" size={26} />
                <h2 className="mt-1 font-bold text-navy-900">વિદ્યાર્થી લોગ ઇન</h2>
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
                <label className="text-sm font-medium text-navy-700">પાસવર્ડ</label>
                <div className="mt-1 flex items-center rounded-xl border border-navy-100 px-3 focus-within:border-brand-blue">
                  <Lock size={18} className="text-navy-300" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && email && password && loginPassword()}
                    placeholder="••••••••"
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
              </div>
              <button
                onClick={loginPassword}
                disabled={!email || !password || busy}
                className="w-full rounded-xl bg-brand-blue text-white py-2.5 text-sm font-semibold hover:bg-navy-800 disabled:opacity-50"
              >
                {busy ? 'લોગ ઇન થાય છે…' : 'લોગ ઇન'}
              </button>
              <div className="text-center text-xs text-navy-400">
                પાસવર્ડ યાદ નથી?{' '}
                <button onClick={() => switchMode('forgot')} className="text-brand-blue font-semibold underline">
                  પાસવર્ડ ભૂલાવો?
                </button>
              </div>
            </div>
          )}

          {mode === 'password' && resetDone && (
            <div className="space-y-3">
              <div className="text-center">
                <Lock className="mx-auto text-brand-green" size={26} />
                <h2 className="mt-1 font-bold text-navy-900">નવો પાસવર્ડ બનાવો</h2>
                <p className="text-xs text-navy-500 mt-1">{email} — ઈમેલ ચકાસાયો ✓</p>
              </div>
              <div>
                <label className="text-sm font-medium text-navy-700">નવો પાસવર્ડ</label>
                <div className="mt-1 flex items-center rounded-xl border border-navy-100 px-3 focus-within:border-brand-blue">
                  <Lock size={18} className="text-navy-300" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
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
              </div>
              <button
                onClick={saveNewPassword}
                disabled={!password || busy}
                className="w-full rounded-xl bg-brand-green text-white py-2.5 text-sm font-semibold hover:opacity-90 disabled:opacity-50"
              >
                {busy ? 'સેવ થાય છે…' : 'પાસવર્ડ સેવ કરો અને લોગ ઇન'}
              </button>
            </div>
          )}

          {mode === 'forgot' && (
            <>
              {!otpSent ? (
                <div className="space-y-3">
                  <div className="text-center">
                    <KeyRound className="mx-auto text-brand-orange" size={26} />
                    <h2 className="mt-1 font-bold text-navy-900">પાસવર્ડ ભૂલાવો?</h2>
                    <p className="text-xs text-navy-500 mt-1">ઈમેલ લખો — OTP થી ચકાસી નવો પાસવર્ડ બનાવશો</p>
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
                  <button
                    onClick={sendOtp}
                    disabled={!email || busy}
                    className="w-full rounded-xl bg-brand-blue text-white py-2.5 text-sm font-semibold hover:bg-navy-800 disabled:opacity-50"
                  >
                    {busy ? 'મોકલી રહ્યા છીએ…' : 'OTP મોકલો'}
                  </button>
                  <div className="text-center text-xs text-navy-400">
                    <button onClick={() => switchMode('password')} className="text-brand-blue font-semibold underline">
                      ← લોગ ઇન પર પાછા જાઓ
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="text-center">
                    <KeyRound className="mx-auto text-brand-orange" size={30} />
                    <h2 className="mt-2 font-bold text-navy-900">OTP દાખલ કરો</h2>
                    <p className="text-xs text-navy-500 mt-1">{email} પર મોકલ્યો છે</p>
                    <div className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-navy-50 px-3 py-1 text-xs font-semibold text-navy-600">
                      <Timer size={13} className="text-brand-orange" />
                      {secondsLeft > 0
                        ? `OTP ${Math.floor(secondsLeft / 60)}:${String(secondsLeft % 60).padStart(2, '0')} માટે માન્ય`
                        : 'OTP સમાપ્ત થયો — ફરી મોકલો'}
                    </div>
                  </div>
                  {devMode && (
                    <div className="rounded-xl bg-amber-50 text-amber-700 text-xs px-3 py-2 text-center">
                      Dev mode — OTP: <b>000000</b>
                    </div>
                  )}
                  <input
                    value={otp}
                    onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    placeholder="6-અંકનો OTP"
                    inputMode="numeric"
                    className="w-full rounded-xl border border-navy-100 px-3 py-3 text-center text-xl font-bold tracking-[0.5em] outline-none focus:border-brand-blue"
                  />
                  <button
                    onClick={verifyOtp}
                    disabled={otp.length < 4 || busy || secondsLeft === 0}
                    className="w-full rounded-xl bg-brand-blue text-white py-2.5 text-sm font-semibold hover:bg-navy-800 disabled:opacity-50"
                  >
                    {busy ? 'ચકાસી રહ્યા છીએ…' : 'ચકાસો'}
                  </button>
                  <div className="flex justify-between text-xs">
                    <button onClick={() => switchMode('password')} className="text-navy-400 underline">
                      ઈમેલ બદલો
                    </button>
                    {resendIn > 0 ? (
                      <span className="text-navy-300">ફરી મોકલો {resendIn}s માં…</span>
                    ) : (
                      <button onClick={sendOtp} disabled={busy} className="text-brand-blue underline font-semibold">
                        ફરી OTP મોકલો
                      </button>
                    )}
                  </div>
                </>
              )}
            </>
          )}

          {mode === 'admin' && (
            <div className="space-y-3">
              <div className="text-center">
                <ShieldCheck className="mx-auto text-navy-900" size={26} />
                <h2 className="mt-1 font-bold text-navy-900">એડમિન લોગ ઇન</h2>
                <p className="text-xs text-navy-500 mt-1">ફક્ત એડમિન માટે</p>
              </div>
              <div>
                <label className="text-sm font-medium text-navy-700">એડમિન ઈમેલ</label>
                <div className="mt-1 flex items-center rounded-xl border border-navy-100 px-3 focus-within:border-brand-blue">
                  <Mail size={18} className="text-navy-300" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="admin@gyansathi.in"
                    className="w-full bg-transparent px-2 py-2.5 text-sm outline-none"
                  />
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-navy-700">પાસવર્ડ</label>
                <div className="mt-1 flex items-center rounded-xl border border-navy-100 px-3 focus-within:border-brand-blue">
                  <Lock size={18} className="text-navy-300" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && email && password && loginPassword()}
                    placeholder="••••••••"
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
              </div>
              <button
                onClick={loginPassword}
                disabled={!email || !password || busy}
                className="w-full rounded-xl bg-navy-900 text-white py-2.5 text-sm font-semibold hover:bg-navy-800 disabled:opacity-50"
              >
                {busy ? 'લોગ ઇન થાય છે…' : 'એડમિન લોગ ઇન'}
              </button>
            </div>
          )}

          {mode !== 'admin' && !otpSent && (
            <div className="text-center text-sm text-navy-500 pt-1">
              એકદમ નવા છો?{' '}
              <Link to="/signup" className="text-base font-bold text-brand-blue">
                સાઇન અપ કરો
              </Link>
            </div>
          )}

          <div className="pt-1 border-t border-navy-100">
            <button
              onClick={() => switchMode(mode === 'admin' ? 'password' : 'admin')}
              className="w-full flex items-center justify-center gap-2 rounded-xl border border-navy-200 text-navy-700 py-2.5 text-sm font-semibold hover:bg-navy-50 transition"
            >
              <ShieldCheck size={16} className="text-navy-500" />
              {mode === 'admin' ? 'વિદ્યાર્થી લોગ ઇન પર પાછા' : 'એડમિન લોગ ઇન'}
            </button>
          </div>

          {info && <div className="rounded-xl bg-navy-50 text-navy-700 text-xs px-3 py-2">{info}</div>}
          {error && <div className="rounded-xl bg-red-50 text-red-600 text-xs px-3 py-2">{error}</div>}
        </div>
      </div>
    </div>
  )
}
