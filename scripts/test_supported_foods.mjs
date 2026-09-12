import assert from 'node:assert/strict'
import { test } from 'node:test'
import { supportedFoods } from '../frontend/lib/generated/supportedFoods.ts'
import { alphabeticalFoods, searchSupportedFoods, supportedFoodExamples } from '../frontend/lib/supportedFoods.ts'

test('supported catalog is complete, alphabetized, and examples are actual model labels', () => {
  assert.equal(supportedFoods.length, 72)
  assert.equal(new Set(supportedFoods.map(food => food.id)).size, 72)
  assert.deepEqual(alphabeticalFoods.map(food => food.name), supportedFoods.map(food => food.name).sort((a, b) => a.localeCompare(b, 'en')))
  assert.deepEqual(supportedFoodExamples.map(food => food.name), ['Idli', 'Dosa', 'Roti', 'Samosa', 'Biryani', 'Palak Paneer'])
})

test('search normalizes case and separators, preserves canonical IDs, and handles empty results', () => {
  for (const query of ['Palak Paneer', 'palak_paneer', ' PALAK--PANEER ', 'palak   paneer']) {
    assert.deepEqual(searchSupportedFoods(query).map(food => food.id), ['palak_paneer'])
  }
  assert.deepEqual(searchSupportedFoods('idli').map(food => food.id), ['idli'])
  assert.deepEqual(searchSupportedFoods('veg biryani').map(food => food.id), ['veg_briyani'])
  assert.deepEqual(searchSupportedFoods('veg_briyani').map(food => food.id), ['veg_briyani'])
  assert.deepEqual(searchSupportedFoods('pizza'), [])
  assert.deepEqual(searchSupportedFoods(''), alphabeticalFoods)
  assert.deepEqual(searchSupportedFoods('   '), alphabeticalFoods)
})
