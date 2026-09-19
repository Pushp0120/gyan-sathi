import { useEffect, useRef, useState } from 'react'
import { Check, Crown, Copy, QrCode, ShieldCheck, Sparkles, Timer } from 'lucide-react'
import { api } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import type { Plan, SubscriptionStatus } from '../types'

interface UpiOrder {
  payment_id: string
  order_id: string
  amount: number
  payee_name: string
  window_seconds: number
  expires_at: string
}

export default function Premium() {
  const { refreshUser } = useAuth()
  const [plans, setPlans] = useState<Plan[]>([])
  const [status, setStatus] = useState<SubscriptionStatus | null>(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  // --- UPI QR payment modal state ---
  const [order, setOrder] = useState<UpiOrder | null>(null)
  const [secondsLeft, setSecondsLeft] = useState(0)
  const [utr, setUtr] = useState('')
  const [verifying, setVerifying] = useState(false)
  const [copied, setCopied] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const load = async () => {
    try {
      const [p, s] = await Promise.all([
        api<{ plans: Plan[] }>('/api/plans'),
        api<SubscriptionStatus>('/api/subscription/status'),
      ])
      setPlans(p.plans)
      setStatus(s)
    } catch {}
  }

  useEffect(() => {
    load()
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
      if (tickRef.current) clearInterval(tickRef.current)
    }
  }, [])

  const premium = plans.find((p) => p.code === 'premium')
  const isPremium = status?.is_premium

  const closeModal = () => {
    setOrder(null)
    setUtr('')
    if (pollRef.current) clearInterval(pollRef.current)
    if (tickRef.current) clearInterval(tickRef.current)
  }

  const startOrder = async () => {
    setBusy(true)
    setError('')
    setMessage('')
    try {
      const o = await api<UpiOrder>('/api/subscription/create', {
        method: 'POST',
        body: JSON.stringify({ plan_code: 'premium' }),
      })
      setOrder(o)
      setSecondsLeft(o.window_seconds)

      // 1-second countdown for the payment window
      if (tickRef.current) clearInterval(tickRef.current)
      tickRef.current = setInterval(() => {
        setSecondsLeft((s) => {
          if (s <= 1) {
            clearInterval(tickRef.current!)
            clearInterval(pollRef.current!)
            return 0
          }
          return s - 1
        })
      }, 1000)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  const verifyUtr = async () => {
    if (!order || utr.trim().length !== 12) {
      setError('12 અંકનો UTR લખો.')
      return
    }
    setVerifying(true)
    setError('')
    try {
      const res = await api<{ ok: boolean }>('/api/subscription/upi/verify', {
        method: 'POST',
        body: JSON.stringify({ payment_id: order.payment_id, utr: utr.trim() }),
      })
      if (res.ok) {
        if (pollRef.current) clearInterval(pollRef.current)
        if (tickRef.current) clearInterval(tickRef.current)
        setMessage('અભિનંદન! Premium સક્રિય થયું 🎉')
        closeModal()
        await load()
        await refreshUser()
      }
    } catch (e: any) {
      setError(e.message)
    } finally {
      setVerifying(false)
    }
  }

  const copyAmount = async () => {
    try {
      await navigator.clipboard.writeText(String(order?.amount ?? ''))
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {}
  }

  const mmss = `${Math.floor(secondsLeft / 60)}:${String(secondsLeft % 60).padStart(2, '0')}`

  return (
    <div className="max-w-md mx-auto px-4 py-8">
      <div className="bg-gradient-to-b from-navy-900 to-brand-blue rounded-3xl p-6 text-white text-center shadow-card">
        <Crown className="mx-auto text-amber-300" size={40} />
        <h1 className="mt-2 text-2xl font-extrabold">Gyan Sathi Premium</h1>
        <div className="mt-3 flex items-end justify-center gap-1">
          <span className="text-4xl font-extrabold">₹{premium?.price_inr ?? 10}</span>
          <span className="text-white/70 text-sm mb-1.5">/વર્ષ</span>
        </div>
        <p className="text-xs text-white/70 mt-1">એક વર્ષ સુધી — દિવસના માત્ર ₹0.03!</p>
      </div>

      {isPremium ? (
        <div className="mt-4 bg-white rounded-2xl shadow-card p-5 text-center space-y-2">
          <ShieldCheck className="mx-auto text-brand-green" size={32} />
          <div className="font-bold text-navy-900">તમે Premium સભ્ય છે ✓</div>
          <div className="text-xs text-navy-500">
            મર્યાદા: {status?.subscription?.expires_at
              ? new Date(status.subscription.expires_at).toLocaleDateString('gu-IN')
              : '—'}
          </div>
        </div>
      ) : (
        <div className="mt-4 bg-white rounded-2xl shadow-card p-5 space-y-3">
          {(premium?.features || [
            '500 uploads',
            'પ્રાધાન્યતા AI એક્સેસ',
            'અદ્યતન ક્વિઝ સુવિધાઓ',
            'વિસ્તૃત ચેટ ઇતિહાસ',
            'Premium બેજ',
            'ભાવિ પ્રીમિયમ સુવિધાઓ',
          ]).map((f) => (
            <div key={f} className="flex items-center gap-2.5 text-sm text-navy-800">
              <Check size={17} className="text-brand-green shrink-0" />
              {f}
            </div>
          ))}
          <button
            onClick={startOrder}
            disabled={busy}
            className="w-full mt-2 rounded-xl bg-brand-orange text-white py-3 text-sm font-extrabold hover:bg-brand-orange-dark disabled:opacity-50"
          >
            {busy ? 'શરૂ થાય છે…' : 'Get Premium 👑'}
          </button>
          <div className="text-center text-[11px] text-navy-400 flex items-center justify-center gap-1">
            <QrCode size={11} /> UPI થી ચૂકવો — QR સ્કેન કરો
          </div>
        </div>
      )}

      {message && <div className="mt-3 rounded-xl bg-green-50 text-green-700 text-sm px-3 py-2.5 text-center">{message}</div>}
      {error && !order && (
        <div className="mt-3 rounded-xl bg-red-50 border border-red-200 text-red-600 text-sm px-3 py-2.5 flex items-start gap-2">
          <span className="shrink-0">⚠️</span>
          <div className="flex-1">પેમેન્ટ શરૂ કરી શકાયો નથી: {error}</div>
          <button onClick={() => setError('')} className="shrink-0 text-red-400 hover:text-red-600">✕</button>
        </div>
      )}

      <p className="mt-4 text-center text-[11px] text-navy-300">
        ચુકવણી પછી UPI રેફરન્સ (UTR) નંબર નાખો — ચકાસણી પછી Premium તરત સક્રિય થશે.
      </p>

      {/* ---------------- UPI QR payment modal ---------------- */}
      {order && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-navy-950/70 backdrop-blur-sm px-4">
          <div className="w-full max-w-sm bg-white rounded-3xl shadow-2xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 font-bold text-navy-900">
                <Crown size={18} className="text-brand-orange" /> UPI ચુકવણી
              </div>
              <div
                className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-bold ${
                  secondsLeft > 30 ? 'bg-navy-50 text-navy-700' : 'bg-red-50 text-red-600 animate-pulse'
                }`}
              >
                <Timer size={13} /> {mmss}
              </div>
            </div>

            {secondsLeft > 0 ? (
              <>
                <div className="rounded-2xl border border-navy-100 p-3 text-center">
                  <img
                    src="/assets/upi-qr.jpeg"
                    alt="UPI QR"
                    className="mx-auto w-52 h-52 object-contain rounded-xl"
                  />
                  <div className="mt-2 text-xs text-navy-500">
                    કોઈપણ UPI એપ (GPay / PhonePe / Paytm) થી સ્કેન કરો
                  </div>
                </div>

                <div className="flex items-center justify-between rounded-xl bg-navy-50 px-3 py-2.5">
                  <div>
                    <div className="text-[10px] text-navy-400 font-semibold uppercase tracking-wide">રકમ</div>
                    <div className="text-lg font-extrabold text-navy-900">₹{order.amount}</div>
                  </div>
                  <button
                    onClick={copyAmount}
                    className="flex items-center gap-1 rounded-lg bg-white border border-navy-100 px-2.5 py-1.5 text-xs font-semibold text-navy-700 hover:bg-navy-50"
                  >
                    <Copy size={13} /> {copied ? 'કૉપિ થયું ✓' : 'કૉપિ'}
                  </button>
                </div>

                <div>
                  <label className="text-sm font-medium text-navy-700">
                    UPI રેફરન્સ નંબર (UTR) <span className="text-navy-400 text-xs">— 12 અંક</span>
                  </label>
                  <input
                    value={utr}
                    onChange={(e) => setUtr(e.target.value.replace(/\D/g, '').slice(0, 12))}
                    inputMode="numeric"
                    placeholder="જેમ કે 4231 8890 1234"
                    className="mt-1 w-full rounded-xl border border-navy-100 px-3 py-2.5 text-sm tracking-widest outline-none focus:border-brand-blue"
                  />
                  <p className="mt-1 text-[11px] text-navy-400">
                    પેમેન્ટ પછી એપમાં "ટ્રાન્ઝેક્શન ID / UTR" મળશે — તે 12 અંક અહીં નાખો.
                  </p>
                </div>

                <button
                  onClick={verifyUtr}
                  disabled={utr.length !== 12 || verifying}
                  className="w-full rounded-xl bg-brand-green text-white py-3 text-sm font-extrabold hover:opacity-90 disabled:opacity-50"
                >
                  {verifying ? 'ચકાસી રહ્યા છીએ…' : 'પેમેન્ટ થઈ ગઈ — ચકાસો ✓'}
                </button>
                <button
                  onClick={closeModal}
                  className="w-full text-center text-xs text-navy-400 underline"
                >
                  રદ કરો
                </button>
                {error && <div className="rounded-xl bg-red-50 text-red-600 text-xs px-3 py-2">{error}</div>}
              </>
            ) : (
              <div className="text-center space-y-3 py-2">
                <div className="text-4xl">⏰</div>
                <div className="font-bold text-navy-900">પેમેન્ટ સમય સમાપ્ત થયો</div>
                <p className="text-xs text-navy-500">
                  2 મિનિટ પૂરી થઈ. જો તમે પૈસા ચૂકવી દીધા હોય તો ચિંતા નહીં — ફરી શરૂ કરીને
                  નવો UTR નાખો, બેવડી ચુકવણી થશે નહીં.
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={closeModal}
                    className="flex-1 rounded-xl border border-navy-200 py-2.5 text-sm font-semibold text-navy-700 hover:bg-navy-50"
                  >
                    બંધ કરો
                  </button>
                  <button
                    onClick={() => { closeModal(); startOrder() }}
                    className="flex-1 rounded-xl bg-brand-orange text-white py-2.5 text-sm font-extrabold hover:bg-brand-orange-dark"
                  >
                    ફરી શરૂ કરો
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
