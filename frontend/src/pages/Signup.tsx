import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { GraduationCap, Lock, Mail, ShieldCheck, Timer } from 'lucide-react'
import Logo from '../components/Logo'
import { api } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import type { User } from '../types'

const OTP_VALIDITY_SEC = 300 // 5 minutes (matches backend OTP_EXPIRE_MINUTES)

export default function Signup() {
  const navigate = useNavigate()
  const { loginWithToken } = useAuth()
  const [step, setStep] = useState<'email' | 'otp'>('email')
  const [email, setEmail] = useState('')
  const [fullName, setFullName] = useState('')
  const [password, setPassword] = useState('')
  const [otp, setOtp] = useState('')
  const [devMode, setDevMode] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')
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

  const sendOtp = async () => {
    setError('')
    setBusy(true)
    try {
      const res = await api<{ sent: boolean; dev_mode?: boolean; message?: string }>(
        '/api/auth/send-otp',
        { method: 'POST', body: JSON.stringify({ email, full_name: fullName }) }
      )
      setStep('otp')
      setSecondsLeft(OTP_VALIDITY_SEC)
      setResendIn(30)
      setOtp('')
      if (res.dev_mode) {
        setDevMode(true)
        setInfo('Dev mode: OTP "000000" વાપરો.')
      } else {
        setInfo('ઈમેલ પર OTP મોકલ્યો છે 📩 — ઇનબોક્સ/સ્પામ તપાસો.')
      }
    } catch (e: any) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  const verify = async () => {
    setError('')
    setBusy(true)
    try {
      const res = await api<{ access_token: string; user: User; needs_onboarding: boolean }>(
        '/api/auth/verify-otp',
        { method: 'POST', body: JSON.stringify({ email, otp, password }) }
      )
      loginWithToken(res.access_token, res.user)
      navigate('/onboarding')
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
            સાઇન અપ — Gyan <span className="text-brand-orange">Sathi</span>
          </h1>
          <p className="text-sm text-navy-500 mt-1">ગુજરાતી વિદ્યાર્થીઓનો AI અભ્યાસ સાથી</p>
        </div>

        <div className="bg-white rounded-2xl shadow-card p-6 space-y-4">
          {step === 'email' ? (
            <>
              <div className="flex items-center gap-2 text-sm text-navy-600 bg-navy-50 rounded-xl px-3 py-2">
                <GraduationCap size={18} className="text-brand-orange" />
                ધોરણ 10 ના વિદ્યાર્થીઓ માટે — સંપૂર્ણ મફત શરૂઆત
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
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && email && sendOtp()}
                    placeholder="ઓછામાં ઓછા 6 અક્ષર"
                    className="w-full bg-transparent px-2 py-2.5 text-sm outline-none"
                  />
                </div>
                <p className="mt-1 text-[11px] text-navy-400">
                  આગળથી આ પાસવર્ડથી સીધા લોગ ઇન કરશો — દર વખતે OTP ની જરૂર નહીં.
                </p>
              </div>
              <button
                onClick={sendOtp}
                disabled={!email || busy}
                className="w-full rounded-xl bg-brand-orange text-white py-2.5 text-sm font-semibold hover:bg-brand-orange-dark disabled:opacity-50"
              >
                {busy ? 'OTP મોકલી રહ્યા છીએ…' : 'OTP મોકલો 📩'}
              </button>
              <div className="text-center text-xs text-navy-400">
                પહેલેથી ખાતું છે?{' '}
                <Link to="/login" className="text-brand-blue font-semibold">
                  લોગ ઇન
                </Link>
              </div>
            </>
          ) : (
            <>
              <div className="text-center">
                <ShieldCheck className="mx-auto text-brand-green" size={30} />
                <h2 className="mt-2 font-bold text-navy-900">ઈમેલ ચકાસો</h2>
                <p className="text-xs text-navy-500 mt-1">{email} પર OTP મોકલ્યો છે</p>
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
                onClick={verify}
                disabled={otp.length < 4 || busy || secondsLeft === 0}
                className="w-full rounded-xl bg-brand-orange text-white py-2.5 text-sm font-semibold hover:bg-brand-orange-dark disabled:opacity-50"
              >
                {busy ? 'ચકાસી રહ્યા છીએ…' : 'ખાતું બનાવો ✓'}
              </button>
              <div className="flex items-center justify-between text-xs">
                <button onClick={() => setStep('email')} className="text-navy-400 underline">
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
          {info && <div className="rounded-xl bg-navy-50 text-navy-700 text-xs px-3 py-2">{info}</div>}
          {error && <div className="rounded-xl bg-red-50 text-red-600 text-xs px-3 py-2">{error}</div>}
        </div>
      </div>
    </div>
  )
}
