import { Link } from 'react-router-dom'
import { Crown, LogOut, Settings, Shield, Sparkles } from 'lucide-react'
import { api } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import Logo from '../components/Logo'
import { useEffect, useState } from 'react'
import type { SubscriptionStatus } from '../types'

export default function Profile() {
  const { user, logout } = useAuth()
  const [status, setStatus] = useState<SubscriptionStatus | null>(null)

  useEffect(() => {
    api<SubscriptionStatus>('/api/subscription/status')
      .then(setStatus)
      .catch(() => {})
  }, [])

  return (
    <div className="max-w-md mx-auto px-4 py-6 space-y-4">
      <div className="bg-gradient-to-br from-navy-900 to-brand-blue rounded-2xl p-6 text-white text-center">
        <div className="w-16 h-16 mx-auto rounded-full bg-white/15 flex items-center justify-center text-2xl font-extrabold">
          {(user?.full_name || 'વિ').charAt(0)}
        </div>
        <h1 className="mt-3 font-extrabold text-lg flex items-center justify-center gap-2">
          {user?.full_name}
          {status?.is_premium && (
            <span
              title="Premium સભ્ય"
              className="rounded-md bg-gradient-to-r from-amber-300 to-amber-400 text-navy-900 px-1.5 py-0.5 text-[10px] font-extrabold tracking-wide leading-none"
            >
              PRO
            </span>
          )}
        </h1>
        <p className="text-xs text-white/70">{user?.email}</p>
        <div className="mt-2 flex justify-center gap-2">
          <span className="rounded-full bg-white/15 px-3 py-1 text-xs">ધોરણ {user?.standard}</span>
          <span className="rounded-full bg-white/15 px-3 py-1 text-xs">
            {user?.medium === 'gujarati' ? 'ગુજરાતી માધ્યમ' : 'English Medium'}
          </span>
          {status?.is_premium && (
            <span className="rounded-full bg-amber-400 text-navy-900 px-3 py-1 text-xs font-bold flex items-center gap-1">
              <Crown size={11} /> Premium
            </span>
          )}
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow-card divide-y divide-navy-50">
        <Link to="/settings" className="flex items-center gap-3 px-4 py-3.5 hover:bg-navy-50 rounded-t-2xl">
          <Settings size={18} className="text-navy-400" />
          <span className="flex-1 text-sm font-medium text-navy-800">સેટિંગ્સ</span>
        </Link>
        <Link to="/premium" className="flex items-center gap-3 px-4 py-3.5 hover:bg-navy-50">
          <Crown size={18} className="text-brand-orange" />
          <span className="flex-1 text-sm font-medium text-navy-800">
            {status?.is_premium ? 'Premium સબસ્ક્રિપ્શન' : 'Premium મેળવો'}
          </span>
          {!status?.is_premium && <Sparkles size={15} className="text-brand-orange" />}
        </Link>
        {user?.role === 'admin' && (
          <Link to="/admin" className="flex items-center gap-3 px-4 py-3.5 hover:bg-navy-50">
            <Shield size={18} className="text-brand-blue" />
            <span className="flex-1 text-sm font-medium text-navy-800">એડમિન પેનલ</span>
          </Link>
        )}
        <button
          onClick={logout}
          className="w-full flex items-center gap-3 px-4 py-3.5 hover:bg-red-50 rounded-b-2xl text-red-500"
        >
          <LogOut size={18} />
          <span className="flex-1 text-sm font-medium text-right-0">લોગ આઉટ</span>
        </button>
      </div>

      <div className="flex justify-center pt-2">
        <Logo size={40} tagline />
      </div>
      <p className="text-center text-[11px] text-navy-300">Gyan Sathi v1.0 · Made for GSEB students 💙</p>
    </div>
  )
}
