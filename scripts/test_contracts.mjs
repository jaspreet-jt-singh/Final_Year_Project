import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import { calculateLocalMacros, resolveCondition } from '../frontend/lib/goals.ts'
import { recommendations, analyzeFood, calculateMacros } from '../frontend/lib/endpoints.ts'
import { sourceUrl } from '../frontend/lib/sourceUrl.ts'

test('nutrition source links allow only absolute HTTP(S) without credentials', () => {
  assert.equal(sourceUrl('https://example.com/food'), 'https://example.com/food')
  for (const value of [null, undefined, '', '/relative', '//example.com', 'javascript:alert(1)', 'data:text/html,hi', 'https://user:pass@example.com']) assert.equal(sourceUrl(value), null)
})

test('frontend macro calculations match every backend policy fixture', () => {
  const fixtures = JSON.parse(readFileSync(new URL('../tests/contracts/macro-fixtures.json', import.meta.url)))
  for (const fixture of fixtures) assert.deepEqual(calculateLocalMacros(fixture.goal, fixture.calories, fixture.condition), fixture.expected)
  assert.equal(resolveCondition('BP'), 'hypertension')
  assert.equal(resolveCondition('diabetes'), 'diabetic')
  assert.throws(() => resolveCondition('diab'), /Unsupported/)
})

test('recommendations reject missing/wrong health context and malformed advice', async () => {
  const original = globalThis.fetch
  const body = { detected_foods: [{ food_label: 'Idli' }], health_condition: 'BP' }
  try {
    for (const result of [
      { recommendations: ['one', 'two', 'three'], source: 'groq' },
      { recommendations: ['one', 'two', 'three'], source: 'groq', health_condition: 'diabetic' },
      { recommendations: ['one', 22, 'three'], source: 'groq', health_condition: 'hypertension' },
    ]) {
      globalThis.fetch = async () => new Response(JSON.stringify(result))
      await assert.rejects(recommendations(body), { kind: 'invalid-response' })
    }
    globalThis.fetch = async () => new Response(JSON.stringify({ recommendations: ['one', 'two', 'three'], source: 'fallback', health_condition: 'hypertension' }))
    assert.equal((await recommendations(body)).health_condition, 'hypertension')
  } finally { globalThis.fetch = original }
})

test('transport retains retry and correlation metadata, and rejects invalid analysis/macros', async () => {
  const original = globalThis.fetch
  try {
    globalThis.fetch = async () => new Response('{"detail":"busy"}', { status: 503, headers: { 'Retry-After': '5', 'X-Request-ID': 'request-123' } })
    await assert.rejects(recommendations({ detected_foods: [] }), { status: 503, retryAfter: 5, requestId: 'request-123', kind: 'server' })
    globalThis.fetch = async () => new Response('{"detections":[{}]}')
    await assert.rejects(analyzeFood(new File(['image'], 'x.jpg')), { kind: 'invalid-response' })
    globalThis.fetch = async () => new Response('{}')
    await assert.rejects(calculateMacros({ goal: 'Maintenance', target_calories: 2000 }), { kind: 'invalid-response' })
  } finally { globalThis.fetch = original }
})
