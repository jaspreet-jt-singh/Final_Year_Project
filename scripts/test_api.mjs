import assert from 'node:assert/strict'
import { test } from 'node:test'
import { apiFetch } from '../frontend/lib/api.ts'

test('unsuccessful responses throw useful errors, not empty detections', async () => {
  const original = globalThis.fetch
  try {
    for (const status of [400, 413, 429, 503]) {
      globalThis.fetch = async () => new Response(JSON.stringify({ detail: 'Upload rejected' }), { status })
      await assert.rejects(apiFetch('/api/analyze-food'), status === 429 ? /Too many requests/ : /Upload rejected/)
    }
  } finally { globalThis.fetch = original }
})
test('timeouts cover response bodies and external cancellation is relayed', async () => {
  const original = globalThis.fetch
  try {
    globalThis.fetch = async (_, { signal }) => ({ text: () => new Promise((_, reject) => signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))) })
    await assert.rejects(apiFetch('/api/analyze-food', {}, 5), { name: 'AbortError' })
    const controller = new AbortController()
    const pending = apiFetch('/api/analyze-food', { signal: controller.signal })
    await Promise.resolve()
    controller.abort()
    await assert.rejects(pending, { name: 'AbortError' })
  } finally { globalThis.fetch = original }
})
test('success clears its timeout instead of aborting later', async () => {
  const original = globalThis.fetch
  let signal
  try {
    globalThis.fetch = async (_, options) => { signal = options.signal; return new Response('{}') }
    await apiFetch('/api/health', {}, 5)
    await new Promise(resolve => setTimeout(resolve, 15))
    assert.equal(signal.aborted, false)
  } finally { globalThis.fetch = original }
})
