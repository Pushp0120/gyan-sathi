import { useEffect, useState } from 'react'
import { Check, Crown, ShieldCheck, Sparkles } from 'lucide-react'
import { api } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import type { Plan, SubscriptionStatus } from '../types'

export default function Premium() {
  const { refreshUser } = useAuth()
  const [plans, setPlans] = useState<Plan[]>([])
  const [status, setStatus] = useState<SubscriptionStatus | null>(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

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
  }, [])

  const premium = plans.find((p) => p.code === 'premium')
  const isPremium = status?.is_premium

  const purchase = async () => {
    setBusy(true)
    setError('')
    setMessage('')
    try {
      // 1. Create order (backend decides sandbox vs live Razorpay)
      const order = await api<{
        payment_id: string
        order_id: string
        amount: number
        mode: string
        gateway: string
        key_id?: string
      }>('/api/subscription/create', {
        method: 'POST',
        body: JSON.stringify({ plan_code: 'premium' }),
      })

      if (order.mode === 'live' && (window as any).Razorpay) {
        // Live flow: open Razorpay checkout, then verify server-side
        const rzp = new (window as any).Razorpay({
          key: order.key_id || order.order_id,
          amount: order.amount * 100,
          currency: 'INR',
          name: 'Gyan Sathi Premium',
          description: 'વાર્ષિક પ્રીમિયમ સબસ્ક્રિપ્શન',
          order_id: order.order_id,
          handler: async (resp: any) => {
            const verify = await api<{ ok: boolean }>('/api/subscription/verify', {
              method: 'POST',
              body: JSON.stringify({
                payment_id: order.payment_id,
                gateway_order_id: resp.razorpay_order_id,
                gateway_payment_id: resp.razorpay_payment_id,
                gateway_signature: resp.razorpay_signature,
              }),
            })
            if (verify.ok) {
              setMessage('અભિનંદન! Premium સક્રિય થયું 🎉')
              await load()
              await refreshUser()
            }
          },
        })
        rzp.open()
      } else {
        // Sandbox flow: simulate a payment token, then server-side verify
        const verify = await api<{ ok: boolean }>('/api/subscription/verify', {
          method: 'POST',
          body: JSON.stringify({
            payment_id: order.payment_id,
            gateway_order_id: order.order_id,
            gateway_payment_id: `sandbox_pay_${Date.now()}`,
            gateway_signature: 'sandbox',
          }),
        })
        if (verify.ok) {
          setMessage('અભિનંદન! Premium સક્રિય થયું 🎉 (ટેસ્ટ મોડ)')
          await load()
          await refreshUser()
        }
      }
    } catch (e: any) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

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
            onClick={purchase}
            disabled={busy}
            className="w-full mt-2 rounded-xl bg-brand-orange text-white py-3 text-sm font-extrabold hover:bg-brand-orange-dark disabled:opacity-50"
          >
            {busy ? 'પ્રક્રિયા ચાલુ છે…' : 'Get Premium 👑'}
          </button>
          {status?.payment_mode === 'sandbox' && (
            <div className="text-center text-[11px] text-amber-600 flex items-center justify-center gap-1">
              <Sparkles size={11} /> ટેસ્ટ મોડ — વાસ્તવિક પેમેન્ટ થશે નહીં
            </div>
          )}
        </div>
      )}

      {message && <div className="mt-3 rounded-xl bg-green-50 text-green-700 text-sm px-3 py-2.5 text-center">{message}</div>}
      {error && <div className="mt-3 rounded-xl bg-red-50 text-red-600 text-xs px-3 py-2">{error}</div>}

      <p className="mt-4 text-center text-[11px] text-navy-300">
        ચુકવણી સુરક્ષિત છે. સબસ્ક્રિપ્શન ફક્ત સર્વર-સાઇડ ચકાસણી પછી જ સક્રિય થાય છે.
      </p>
    </div>
  )
}
