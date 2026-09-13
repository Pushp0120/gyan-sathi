const API_BASE = ''

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export function getToken(): string | null {
  return localStorage.getItem('gs_token')
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem('gs_token', token)
  else localStorage.removeItem('gs_token')
}

export async function api<T = any>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  }
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })

  if (res.status === 401 && !path.includes('/auth/')) {
    setToken(null)
    window.location.href = '/login'
    throw new ApiError(401, 'સત્ર સમાપ્ત થયું છે. ફરી લોગ ઇન કરો.')
  }

  let data: any = null
  try {
    data = await res.json()
  } catch {
    /* non-JSON */
  }

  if (!res.ok) {
    throw new ApiError(res.status, data?.detail || 'કંઈક સમસ્યા આવી છે. થોડીવાર પછી ફરી પ્રયાસ કરો.')
  }
  return data as T
}

export async function apiStream(
  path: string,
  body: unknown,
  onDelta: (text: string) => void,
  onDone: (meta: any) => void,
  onError: (msg: string) => void
): Promise<void> {
  const token = getToken()
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
    })
    if (!res.ok || !res.body) {
      let detail = 'કંઈક સમસ્યા આવી છે.'
      try {
        const j = await res.json()
        detail = j.detail || detail
      } catch {}
      onError(detail)
      return
    }
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n\n')
      buffer = parts.pop() || ''
      for (const part of parts) {
        const line = part.trim()
        if (!line.startsWith('data:')) continue
        try {
          const evt = JSON.parse(line.slice(5).trim())
          if (evt.type === 'delta') onDelta(evt.content)
          else if (evt.type === 'done') onDone(evt)
          else if (evt.type === 'error') onError(evt.content)
        } catch {}
      }
    }
    onDone({})
  } catch {
    onError('નેટવર્ક સમસ્યા. થોડીવાર પછી ફરી પ્રયાસ કરો.')
  }
}
