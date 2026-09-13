import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import {
  BookOpen,
  Brain,
  Crown,
  LayoutDashboard,
  LogOut,
  MessageCircle,
  Shield,
  Upload,
  User as UserIcon,
} from 'lucide-react'
import Logo from './Logo'
import { useAuth } from '../contexts/AuthContext'

const studentNav = [
  { to: '/dashboard', label: 'હોમ', icon: LayoutDashboard },
  { to: '/chat', label: 'ચેટ', icon: MessageCircle },
  { to: '/subjects', label: 'વિષયો', icon: BookOpen },
  { to: '/quiz', label: 'ક્વિઝ', icon: Brain },
  { to: '/progress', label: 'પ્રગતિ', icon: Brain },
  { to: '/uploads', label: 'અપલોડ', icon: Upload },
  { to: '/premium', label: 'પ્રીમિયમ', icon: Crown },
  { to: '/profile', label: 'પ્રોફાઇલ', icon: UserIcon },
]

const mobileNav = [
  { to: '/dashboard', label: 'હોમ', icon: LayoutDashboard },
  { to: '/chat', label: 'ચેટ', icon: MessageCircle },
  { to: '/subjects', label: 'વિષયો', icon: BookOpen },
  { to: '/quiz', label: 'ક્વિઝ', icon: Brain },
  { to: '/profile', label: 'પ્રોફાઇલ', icon: UserIcon },
]

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  if (!user) return null

  const isAdmin = user.role === 'admin'

  return (
    <div className="flex h-full">
      {/* Desktop sidebar */}
      <aside className="hidden md:flex w-64 flex-col bg-white border-r border-navy-100 px-4 py-5">
        <Logo size={42} tagline />
        <nav className="mt-8 flex-1 space-y-1">
          {studentNav.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
                  isActive
                    ? 'bg-navy-50 text-navy-900 shadow-sm'
                    : 'text-navy-500 hover:bg-navy-50 hover:text-navy-800'
                }`
              }
            >
              <Icon size={19} className={to === '/premium' ? 'text-brand-orange' : ''} />
              {label}
            </NavLink>
          ))}
          {isAdmin && (
            <NavLink
              to="/admin"
              className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold text-brand-blue hover:bg-navy-50"
            >
              <Shield size={19} />
              એડમિન પેનલ
            </NavLink>
          )}
        </nav>
        <button
          onClick={() => {
            logout()
            navigate('/login')
          }}
          className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-red-500 hover:bg-red-50"
        >
          <LogOut size={19} />
          લોગ આઉટ
        </button>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile header */}
        <header className="md:hidden sticky top-0 z-20 flex items-center justify-between bg-white/95 backdrop-blur border-b border-navy-100 px-4 py-2.5">
          <Logo size={34} withText />
          <div className="flex items-center gap-2">
            {isAdmin && (
              <button
                onClick={() => navigate('/admin')}
                className="p-2 rounded-lg text-brand-blue hover:bg-navy-50"
                aria-label="Admin"
              >
                <Shield size={20} />
              </button>
            )}
            <button
              onClick={() => {
                logout()
                navigate('/login')
              }}
              className="p-2 rounded-lg text-red-500 hover:bg-red-50"
              aria-label="Logout"
            >
              <LogOut size={20} />
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto pb-20 md:pb-0">
          <Outlet />
        </main>

        {/* Mobile bottom nav */}
        <nav className="md:hidden fixed bottom-0 inset-x-0 z-30 bg-white border-t border-navy-100 pb-safe">
          <div className="grid grid-cols-5">
            {mobileNav.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `flex flex-col items-center py-2 text-[11px] font-medium ${
                    isActive ? 'text-brand-blue' : 'text-navy-400'
                  }`
                }
              >
                <Icon size={21} />
                {label}
              </NavLink>
            ))}
          </div>
        </nav>
      </div>
    </div>
  )
}
