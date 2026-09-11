const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ??
  (process.env.NODE_ENV === 'development' ? 'http://localhost:8000' : '')

export type ApiErrorKind = 'cancelled' | 'timeout' | 'invalid-response' | 'rate-limit' | 'server' | 'request' | 'network'
export class ApiError extends Error {
  constructor(message: string, public kind: ApiErrorKind, public status?: number, public retryAfter?: number, public requestId?: string) {
    super(message)
    this.name = 'ApiError'
  }
}

export async function apiFetch(path: string, options: RequestInit = {}, timeoutMs = 30000): Promise<Response> {
  const controller = new AbortController()
  let timedOut = false
  const relayAbort = () => controller.abort()
  options.signal?.addEventListener('abort', relayAbort, { once: true })
  if (options.signal?.aborted) controller.abort()
  const timer = setTimeout(() => { timedOut = true; controller.abort() }, timeoutMs)
  try {
    const response = await fetch(`${API_BASE}${path}`, { ...options, signal: controller.signal })
    const content = await response.text()
    if (!response.ok) {
      let message = `Request failed (status ${response.status})`
      try { const error = JSON.parse(content); if (typeof error.detail === 'string') message = error.detail; else if (typeof error.message === 'string') message = error.message } catch { /* Non-JSON gateway response. */ }
      const header = response.headers.get('Retry-After')
      const retryAfter = header ? /^\d+$/.test(header) ? Number(header) : Math.max(0, Math.ceil((Date.parse(header) - Date.now()) / 1000)) : undefined
      if (response.status === 429) message = 'Too many requests. Please wait a minute and try again.'
      throw new ApiError(message, response.status === 429 ? 'rate-limit' : response.status >= 500 ? 'server' : 'request', response.status, Number.isFinite(retryAfter) ? retryAfter : undefined, response.headers.get('X-Request-ID') ?? undefined)
    }
    return new Response(content, { status: response.status, headers: response.headers })
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (timedOut) throw new ApiError('The request took too long. Please wait a moment and try again.', 'timeout')
    if (options.signal?.aborted) throw new ApiError('Request cancelled.', 'cancelled')
    throw new ApiError('Could not connect. Please check your connection and try again.', 'network')
  } finally { clearTimeout(timer); options.signal?.removeEventListener('abort', relayAbort) }
}
