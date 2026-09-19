import { useEffect, useRef, useState } from 'react'
import { api } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import type { User } from '../types'

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string
            callback: (response: { credential?: string }) => void
            auto_select?: boolean
            cancel_on_tap_outside?: boolean
          }) => void
          renderButton: (
            parent: HTMLElement,
            options: Record<string, unknown>
          ) => void
          prompt: () => void
        }
      }
    }
  }
}

interface Props {
  onSuccess?: (user: User, needsOnboarding: boolean) => void
  /** Official GIS theme; 'dark' looks premium on white cards too */
  theme?: 'outline' | 'filled_blue' | 'filled_black'
  text?: 'signin_with' | 'signup_with' | 'continue_with'
  className?: string
}

/**
 * Official Google Sign-In (GIS) button. Renders Google's own button via
 * gsi script (loaded in index.html); exchanges the returned ID token for an
 * app JWT at POST /api/auth/google. Hidden entirely when GOOGLE_CLIENT_ID
 * is not configured server-side.
 */
export default function GoogleSignInButton({
  onSuccess,
  theme = 'filled_blue',
  text = 'signup_with',
  className = '',
}: Props) {
  const { loginWithToken } = useAuth()
  const divRef = useRef<HTMLDivElement>(null)
  const [state, setState] = useState<'loading' | 'ready' | 'hidden' | 'error'>('loading')
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false

    async function init() {
      try {
        const status = await api<{ enabled: boolean; client_id: string }>('/api/auth/google/status')
        if (!status.enabled || !status.client_id) {
          if (!cancelled) setState('hidden')
          return
        }
        // Wait for the gsi script from index.html (it is loaded async)
        const waitForGsi = (): Promise<void> =>
          new Promise((resolve, reject) => {
            if (window.google?.accounts?.id) return resolve()
            let waited = 0
            const iv = setInterval(() => {
              waited += 100
              if (window.google?.accounts?.id) {
                clearInterval(iv)
                resolve()
              } else if (waited > 5000) {
                clearInterval(iv)
                reject(new Error('Google script load timeout'))
              }
            }, 100)
          })
        await waitForGsi()
        if (cancelled || !divRef.current) return

        window.google!.accounts.id.initialize({
          client_id: status.client_id,
          callback: (response) => {
            if (!response.credential) {
              setError('Google સાઇન ઇન રદ થયું.')
              return
            }
            handleCredential(response.credential)
          },
          cancel_on_tap_outside: true,
        })
        window.google!.accounts.id.renderButton(divRef.current, {
          theme,
          size: 'large',
          shape: 'pill',
          text,
          width: 320,
          logo_alignment: 'center',
        })
        setState('ready')
      } catch {
        if (!cancelled) setState('hidden') // backend unreachable → just hide
      }
    }

    init()
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleCredential = async (credential: string) => {
    setError('')
    try {
      const res = await api<{ access_token: string; user: User; needs_onboarding: boolean }>(
        '/api/auth/google',
        { method: 'POST', body: JSON.stringify({ credential }) }
      )
      loginWithToken(res.access_token, res.user)
      onSuccess?.(res.user, res.needs_onboarding)
    } catch (e: any) {
      setError(e.message)
    }
  }

  if (state === 'hidden') return null

  return (
    <div className={className}>
      <div className="flex items-center gap-3 py-1">
        <div className="h-px flex-1 bg-navy-100" />
        <span className="text-xs font-medium text-navy-400">અથવા</span>
        <div className="h-px flex-1 bg-navy-100" />
      </div>
      {state === 'loading' && (
        <div className="h-10 animate-pulse rounded-full bg-navy-50" aria-hidden />
      )}
      <div ref={divRef} className="flex justify-center" />
      {error && (
        <div className="mt-2 rounded-xl bg-red-50 text-red-600 text-xs px-3 py-2 text-center">
          {error}
        </div>
      )}
    </div>
  )
}
