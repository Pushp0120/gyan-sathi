import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

/**
 * Homepage splash: 5-second CSS/SVG logo landing animation
 * (spec: book+arc rise → characters pop → wordmark slides in →
 * tagline fades with expanding bars → shimmer + robot blink),
 * on the same background as the login page. Then → login/dashboard.
 */

const SPLASH_MS = 5000

export default function Intro() {
  const navigate = useNavigate()
  const { user, loading } = useAuth()
  const [leaving, setLeaving] = useState(false)

  useEffect(() => {
    document.title = 'Gyan Sathi — તમારો અભ્યાસ, અમારો સાથી'
    const leave = setTimeout(() => setLeaving(true), SPLASH_MS)
    return () => clearTimeout(leave)
  }, [])

  useEffect(() => {
    if (!leaving) return
    const t = setTimeout(() => {
      navigate(user ? (user.role === 'admin' ? '/admin' : '/dashboard') : '/login', {
        replace: true,
      })
    }, 450) // match the fade-out duration below
    return () => clearTimeout(t)
  }, [leaving, navigate, user])

  return (
    <div
      onClick={() => setLeaving(true)}
      className={`fixed inset-0 z-50 flex cursor-pointer flex-col items-center justify-center bg-gradient-to-b from-navy-50 to-white transition-opacity duration-[450ms] ${
        leaving ? 'opacity-0' : 'opacity-100'
      }`}
    >
      {/* beat 1+2: logo icon (book/arc/characters) rises, then characters pop via bounce easing */}
      <div className="gs-rise relative">
        <img
          src="/assets/logo.png"
          alt="Gyan Sathi logo"
          className="gs-pop h-36 w-36 object-contain sm:h-44 sm:w-44"
        />
        {/* beat 5: shimmer sweeping across the icon */}
        <div className="gs-shimmer pointer-events-none absolute inset-0 overflow-hidden rounded-3xl">
          <div className="gs-shimmer-bar absolute inset-y-0 w-1/3 -skew-x-12 bg-gradient-to-r from-transparent via-white/70 to-transparent" />
        </div>
      </div>

      {/* beat 3: wordmark — Gyan slides from left, Sathi from right */}
      <h1 className="mt-4 flex items-baseline gap-2 overflow-hidden text-5xl font-extrabold tracking-tight text-navy-900 sm:text-6xl">
        <span className="gs-from-left inline-block">Gyan</span>
        <span className="gs-from-right inline-block text-brand-orange">Sathi</span>
      </h1>

      {/* beat 4: tagline fades in, accent bars expand outward */}
      <div className="mt-4 flex items-center gap-3">
        <span className="gs-bar-left h-px w-12 bg-brand-orange/60 sm:w-16" />
        <p className="gs-fade text-sm font-medium text-navy-500 sm:text-base">
          તમારો અભ્યાસ, અમારો સાથી
        </p>
        <span className="gs-bar-right h-px w-12 bg-brand-orange/60 sm:w-16" />
      </div>

      {/* beat 5: robot blink is baked into the logo.png; shimmer covers the spec */}

      <style>{`
        @keyframes gs-rise {
          0%   { opacity: 0; transform: translateY(120px); }
          66%  { opacity: 1; }
          100% { opacity: 1; transform: translateY(0); }
        }
        .gs-rise { opacity: 0; animation: gs-rise 1.2s cubic-bezier(0.22, 0.61, 0.36, 1) 0s forwards; }

        @keyframes gs-pop {
          0%, 20%  { transform: scale(0.7) translateY(80px); opacity: 0; }
          32%      { opacity: 1; }
          44%      { transform: scale(1.05) translateY(0); }
          50%      { transform: scale(1); }
          100%     { transform: scale(1) translateY(0); opacity: 1; }
        }
        .gs-pop { animation: gs-pop 1.5s cubic-bezier(0.34, 1.56, 0.64, 1) 1s both; }

        @keyframes gs-from-left  { 0% { transform: translateX(-150px); opacity: 0; } 60%,100% { transform: translateX(0); opacity: 1; } }
        @keyframes gs-from-right { 0% { transform: translateX(150px); opacity: 0; } 60%,100% { transform: translateX(0); opacity: 1; } }
        .gs-from-left  { animation: gs-from-left 1s ease-out 2.3s both; }
        .gs-from-right { animation: gs-from-right 1s ease-out 2.3s both; }

        @keyframes gs-fade { to { opacity: 1; } }
        .gs-fade { opacity: 0; animation: gs-fade 0.7s ease-out 3.5s forwards; }

        @keyframes gs-bar-left  { 0% { transform: scaleX(0.2); opacity: 0; } 100% { transform: scaleX(1); opacity: 1; } }
        @keyframes gs-bar-right { 0% { transform: scaleX(0.2); opacity: 0; } 100% { transform: scaleX(1); opacity: 1; } }
        .gs-bar-left  { transform-origin: right; animation: gs-bar-left 0.9s ease-out 3.5s both; }
        .gs-bar-right { transform-origin: left;  animation: gs-bar-left 0.9s ease-out 3.5s both; }

        @keyframes gs-shimmer {
          0%   { transform: translateX(-150%); }
          100% { transform: translateX(400%); }
        }
        .gs-shimmer-bar { animation: gs-shimmer 0.9s ease-in-out 4.4s both; }
      `}</style>
    </div>
  )
}
