import assert from 'node:assert/strict'
import { test } from 'node:test'
import { createDraft, emptyJournal, localDate, millisecondsToMidnight, parseJournal, saveDraft, sameItems, totalNutrition } from '../frontend/lib/meals.ts'

const analysis = { detections: [{ food_label: 'Idli', display_name: 'Idli', confidence: .9, bounding_box: [0, 0, 100, 100], macros: { calories: 100, protein_g: 3, carbs_g: 20, fat_g: 1 }, macros_unit: 'per_100g', nutrition_source: 'INDB' }], img_width: 100, img_height: 100, food_not_found: false }

test('portions scale from 100 g without rounding intermediate values', () => {
  const draft = createDraft(analysis, 'one')
  assert.equal(draft.items[0].grams, 100)
  draft.items[0].grams = 125
  assert.deepEqual(totalNutrition(draft.items), { calories: 125, protein_g: 3.75, carbs_g: 25, fat_g: 1.25, knownItems: 1, itemCount: 1, incomplete: false })
  draft.items[0].included = false
  assert.equal(totalNutrition(draft.items).itemCount, 0)
  assert.throws(() => saveDraft([], draft), /Include/)
})
test('unknown nutrition is explicitly incomplete and excluded unknown foods do not affect totals', () => {
  const draft = createDraft({ ...analysis, detections: [...analysis.detections, { ...analysis.detections[0], macros: null }] }, 'two')
  assert.equal(totalNutrition(draft.items).incomplete, true)
  assert.equal(totalNutrition(draft.items).knownItems, 1)
  draft.items[1].included = false
  assert.equal(totalNutrition(draft.items).incomplete, false)
})
test('save and update preserve identity/date; new scans remain separate', () => {
  const draft = createDraft(analysis, 'one')
  const now = new Date(2026, 8, 11, 23, 55)
  let meals = saveDraft([], draft, now)
  meals = saveDraft(meals, draft, now)
  assert.equal(meals.length, 1)
  draft.items = draft.items.map(item => ({ ...item, grams: 200 }))
  meals = saveDraft(meals, draft, new Date(2026, 8, 12))
  assert.equal(meals[0].localDate, '2026-09-11')
  assert.equal(meals[0].savedAt, now.toISOString())
  assert.equal(totalNutrition(meals[0].items).calories, 200)
  meals = saveDraft(meals, createDraft(analysis, 'two'), new Date(2026, 8, 12))
  assert.equal(meals.length, 2)
  assert.equal(meals[0].id, 'two')
})
test('versioned records round trip with strict validation and no private fields', () => {
  const journal = { ...emptyJournal(), meals: saveDraft([], createDraft(analysis, 'one')) }
  assert.deepEqual(parseJournal(JSON.stringify(journal)), journal)
  assert.equal(sameItems(parseJournal(JSON.stringify(journal)).meals[0].items, journal.meals[0].items), true)
  assert.deepEqual(parseJournal(null), emptyJournal())
  assert.throws(() => parseJournal('{bad'), SyntaxError)
  assert.throws(() => parseJournal('{"version":2}'), /unsupported/)
  const bad = structuredClone(journal)
  bad.meals[0].items[0].grams = 26
  assert.throws(() => parseJournal(JSON.stringify(bad)), /damaged/)
  bad.meals[0].items[0].grams = 100
  bad.meals[0].localDate = '2026-02-31'
  assert.throws(() => parseJournal(JSON.stringify(bad)), /damaged/)
  const extras = { ...journal, photo: 'secret-photo', healthCondition: 'private' }
  assert.equal(JSON.stringify(parseJournal(JSON.stringify(extras))).includes('private'), false)
  assert.equal(JSON.stringify(parseJournal(JSON.stringify(extras))).includes('secret-photo'), false)
})
test('local calendar dates and midnight scheduling follow the local clock', () => {
  assert.equal(localDate(new Date(2026, 8, 11, 23, 59)), '2026-09-11')
  assert.equal(localDate(new Date(2026, 8, 12, 0, 0)), '2026-09-12')
  assert.equal(millisecondsToMidnight(new Date(2026, 8, 11, 23, 59, 59)), 1000)
})
