import { useEffect, useState } from 'react'
import { Crown } from 'lucide-react'
import { api } from '../../services/api'

export default function AdminSubscriptions() {
  const [subs, setSubs] = useState<any[]>([])
  const [payments, setPayments] = useState<any[]>([])

  useEffect(() => {
    api<{ subscriptions: any[] }>('/api/admin/subscriptions').then((r) => setSubs(r.subscriptions)).catch(() => {})
    api<{ payments: any[] }>('/api/admin/payments').then((r) => setPayments(r.payments)).catch(() => {})
  }, [])

  return (
    <div className="p-4 md:p-6 space-y-6">
      <h1 className="text-lg font-bold text-navy-900">સબસ્ક્રિપ્શન અને પેમેન્ટ</h1>

      <section>
        <h2 className="font-semibold text-navy-800 mb-2">સક્રિય/તાજી સબસ્ક્રિપ્શન ({subs.length})</h2>
        <div className="bg-white rounded-2xl shadow-card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-navy-400 border-b border-navy-100">
                <th className="px-4 py-3">વિદ્યાર્થી</th>
                <th className="px-4 py-3">પ્લાન</th>
                <th className="px-4 py-3">સ્થિતિ</th>
                <th className="px-4 py-3">સમાપ્તિ</th>
              </tr>
            </thead>
            <tbody>
              {subs.map((s) => (
                <tr key={s.id} className="border-b border-navy-50">
                  <td className="px-4 py-3">{s.student_email}</td>
                  <td className="px-4 py-3">
                    {s.plan?.code === 'premium' && (
                      <span className="inline-flex items-center gap-1 text-amber-600 font-semibold">
                        <Crown size={12} /> Premium
                      </span>
                    )}
                    {s.plan?.code === 'free' && 'મફત'}
                  </td>
                  <td className="px-4 py-3">
                    <span className={s.status === 'active' ? 'text-brand-green font-semibold' : 'text-navy-400'}>
                      {s.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-navy-500">
                    {s.expires_at ? new Date(s.expires_at).toLocaleDateString('gu-IN') : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {subs.length === 0 && <div className="text-center text-sm text-navy-400 py-6">કોઈ સબસ્ક્રિપ્શન નથી.</div>}
        </div>
      </section>

      <section>
        <h2 className="font-semibold text-navy-800 mb-2">પેમેન્ટ રેકોર્ડ ({payments.length})</h2>
        <div className="bg-white rounded-2xl shadow-card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-navy-400 border-b border-navy-100">
                <th className="px-4 py-3">વિદ્યાર્થી</th>
                <th className="px-4 py-3">રકમ</th>
                <th className="px-4 py-3">ગેટવે</th>
                <th className="px-4 py-3">સ્થિતિ</th>
                <th className="px-4 py-3">તારીખ</th>
              </tr>
            </thead>
            <tbody>
              {payments.map((p) => (
                <tr key={p.id} className="border-b border-navy-50">
                  <td className="px-4 py-3">{p.student_email}</td>
                  <td className="px-4 py-3 font-semibold">₹{p.amount_inr}</td>
                  <td className="px-4 py-3 text-xs">{p.gateway} ({p.mode})</td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-bold ${
                        p.status === 'paid'
                          ? 'bg-green-100 text-green-700'
                          : p.status === 'failed'
                          ? 'bg-red-100 text-red-600'
                          : 'bg-slate-100 text-slate-500'
                      }`}
                    >
                      {p.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-navy-500">
                    {p.created_at ? new Date(p.created_at).toLocaleDateString('gu-IN') : ''}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {payments.length === 0 && <div className="text-center text-sm text-navy-400 py-6">કોઈ પેમેન્ટ નથી.</div>}
        </div>
      </section>
    </div>
  )
}
