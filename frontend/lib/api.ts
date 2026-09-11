const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ??
  (process.env.NODE_ENV === 'development' ? 'http://localhost:8000' : '')

export async function apiFetch(path: string, options: RequestInit = {}, timeoutMs = 30000): Promise<Response> {
  const controller = new AbortController()
  const relayAbort = () => controller.abort()
  options.signal?.addEventListener('abort', relayAbort, { once: true })
  if (options.signal?.aborted) controller.abort()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const response = await fetch(`${API_BASE}${path}`, { ...options, signal: controller.signal })
    const content = await response.text()
    if (!response.ok) {
      let message = `Request failed (status ${response.status})`
      try {
        const error = JSON.parse(content)
        if (typeof error.detail === 'string') message = error.detail
        else if (typeof error.message === 'string') message = error.message
      } catch { /* Upstream errors may not be JSON. */ }
      if (response.status === 429) message = 'Too many requests. Please wait a minute and try again.'
      throw new Error(message)
    }
    return new Response(content, { status: response.status, headers: response.headers })
  } finally {
    clearTimeout(timer)
    options.signal?.removeEventListener('abort', relayAbort)
  }
}
