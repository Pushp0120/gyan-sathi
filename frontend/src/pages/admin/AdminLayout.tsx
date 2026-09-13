import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import {
  BarChart3, BookOpen, ChevronLeft, CreditCard, Database, GraduationCap,
  LayoutDashboard, ListTree,
} from 'lucide-react'
import Logo from '../../components/Logo'

const nav = [
  { to: '/admin', label: 'ડેશબોર્ડ', icon: LayoutDashboard, end: true },
  { to: '/admin/students', label: 'વિદ્યાર્થીઓ', icon: GraduationCap },
  { to: '/admin/subjects', label: 'વિષયો', icon: BookOpen },
  { to: '/admin/chapters', label: 'પ્રકરણો', icon: ListTree },
  { to: '/admin/knowledge', label: 'જ્ઞાન કોશ', icon: Database },
  { to: '/admin/subscriptions', label: 'સબસ્ક્રિપ્શન', icon: CreditCard },
  { to: '/admin/analytics', label: 'વિશ્લેષણ', icon: BarChart3 },
]

export default function AdminLayout() {
  const navigate = useNavigate()
  return (
    <div className="flex h-full">
      <aside className="hidden md:flex w-60 flex-col bg-navy-950 text-white px-4 py-5">
        <div className="flex items-center gap-2 mb-8">
          <Logo size={36} withText={false} />
          <div>
            <div className="font-bold text-sm">Gyan Sathi</div>
            <div className="text-[10px] text-white/50 font-semibold tracking-widest">ADMIN PANEL</div>
          </div>
        </div>
        <nav className="flex-1 space-y-1">
          {nav.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
                  isActive ? 'bg-white/15 text-white' : 'text-white/60 hover:bg-white/10 hover:text-white'
                }`
              }
            >
              <Icon size={17} />
              {label}
            </NavLink>
          ))}
        </nav>
        <button
          onClick={() => navigate('/dashboard')}
          className="flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm text-white/60 hover:bg-white/10"
        >
          <ChevronLeft size={16} /> સ્ટુડન્ટ વ્યૂ
        </button>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="md:hidden sticky top-0 z-20 flex items-center gap-2 bg-navy-950 text-white px-4 py-2.5 overflow-x-auto">
          <Logo size={28} withText={false} />
          {nav.map(({ to, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `shrink-0 rounded-full px-3 py-1.5 text-xs font-medium ${
                  isActive ? 'bg-white text-navy-900' : 'bg-white/10 text-white/80'
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </header>
        <main className="flex-1 overflow-y-auto bg-slate-50">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
