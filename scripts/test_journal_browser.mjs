import assert from 'node:assert/strict'
import { launchBrowser, mockMacros } from './browser_support.mjs'

const browser = await launchBrowser()
const url = 'http://127.0.0.1:4173'
const key = 'food-recognition.journal'
const food = { food_label: 'Idli', display_name: 'Idli', confidence: .9, bounding_box: [10, 10, 80, 80], macros: { calories: 100, protein_g: 3, carbs_g: 20, fat_g: 1 }, macros_unit: 'per_100g', nutrition_source: 'INDB' }
const errors = []
let guidanceCalls = 0
let scenario = 'success'
async function setup(options = {}) {
  const context = await browser.newContext(options)
  const page = await context.newPage()
  page.on('pageerror', error => errors.push(error.message))
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname
    let status = 200, body = {}
    if (path.endsWith('/goals')) body = { goals: [] }
    if (path.endsWith('/health-conditions')) body = { health_conditions: [] }
    if (path.endsWith('/calculate-macros')) {
      const input = route.request().postDataJSON()
      body = mockMacros(input)
      if (input.target_calories === 2200) await new Promise(resolve => setTimeout(resolve, 1200))
    }
    if (path.endsWith('/recommendations')) { guidanceCalls++; body = { recommendations: ['One', 'Two', 'Three'], source: 'fallback', health_condition: route.request().postDataJSON().health_condition || 'none' }; if (scenario === 'advice-failure') { status = 503; body = { detail: 'Guidance unavailable' } } }
    if (path.endsWith('/analyze-food')) body = { detections: scenario === 'unknown' ? [food, { ...food, food_label: 'Unknown', display_name: 'Unknown dish', macros: null }] : [food], img_width: 100, img_height: 100, food_not_found: false }
    await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) })
  })
  return { page, context }
}
async function upload(page) {
  const png = await page.evaluate(() => { const canvas = document.createElement('canvas'); canvas.width = canvas.height = 100; canvas.getContext('2d').fillRect(0, 0, 100, 100); return canvas.toDataURL().split(',')[1] })
  await page.locator('input[type=file]').setInputFiles({ name: 'food.png', mimeType: 'image/png', buffer: Buffer.from(png, 'base64') })
  await page.getByRole('button', { name: 'Save meal', exact: true }).waitFor()
}
const read = page => page.evaluate(key => JSON.parse(localStorage.getItem(key)), key)
const count = page => page.locator('#history article').count()
async function waitText(locator, text) { await locator.filter({ hasText: text }).waitFor() }
try {
  const { page, context } = await setup({ viewport: { width: 1280, height: 900 } })
  await page.goto(url)
  await page.getByRole('button', { name: 'Choose Image', exact: true }).focus()
  const picker = page.waitForEvent('filechooser')
  await page.keyboard.press('Enter'); await picker
  await upload(page)
  assert.equal(await count(page), 0)
  assert.match(await page.locator('.daily-number').innerText(), /^0/)
  await page.getByText('Local fallback suggestions', { exact: false }).waitFor()
  const beforePortionCalls = guidanceCalls
  await page.getByRole('button', { name: 'Increase Idli portion' }).click()
  await page.getByRole('button', { name: 'Save meal', exact: true }).click()
  await page.getByRole('button', { name: 'Meal saved', exact: true }).waitFor()
  assert.equal(await count(page), 1)
  assert.match(await page.locator('.daily-number').innerText(), /^125/)
  assert.equal((await read(page)).meals[0].items[0].grams, 125)
  await page.getByRole('button', { name: 'Increase Idli portion' }).click()
  await page.getByRole('button', { name: 'Update saved meal' }).click()
  assert.equal(await count(page), 1)
  assert.match(await page.locator('.daily-number').innerText(), /^150/)
  assert.equal(guidanceCalls, beforePortionCalls)
  await page.getByRole('button', { name: 'Choose another image' }).click()
  assert.equal(await page.getByRole('button', { name: 'Save meal', exact: true }).count(), 0)
  assert.match(await page.locator('.daily-number').innerText(), /^150/)
  await page.reload(); await waitText(page.locator('.daily-number'), '150')
  await page.getByRole('button', { name: 'Edit portions' }).click()
  await page.getByRole('button', { name: 'Decrease Idli portion' }).click()
  await page.getByRole('button', { name: 'Save changes' }).click()
  assert.match(await page.locator('.daily-number').innerText(), /^125/)
  await page.getByRole('button', { name: 'Delete meal', exact: true }).click()
  assert.equal(await count(page), 0)
  await page.getByRole('button', { name: 'Undo delete' }).click()
  assert.equal(await count(page), 1)
  await page.getByText('Goals & advanced settings', { exact: true }).click()
  await page.getByLabel('Daily calorie target').fill('2200')
  await page.getByRole('button', { name: 'Save goals' }).click()
  await page.waitForTimeout(350)
  await page.getByLabel('Daily calorie target').fill('2500')
  await page.getByRole('button', { name: 'Save goals' }).click()
  await page.getByLabel('Health context (this session only)').selectOption('diabetic')
  await page.waitForTimeout(1400)
  assert.equal((await read(page)).preferences.calories, 2500)
  await page.getByText('Protein 250 g · Carbs 250 g · Fat 56 g', { exact: true }).waitFor()
  const stored = JSON.stringify(await read(page))
  assert.equal(/Diabetic|imageUrl|data:image|blob:|bounding_box|confidence/.test(stored), false)
  await page.reload(); await waitText(page.locator('.daily-summary'), '2,500')
  await page.getByText('Goals & advanced settings', { exact: true }).click()
  assert.equal(await page.getByLabel('Health context (this session only)').inputValue(), 'none')
  await page.getByRole('button', { name: 'Clear history', exact: true }).click()
  await page.getByRole('button', { name: 'Keep history' }).click()
  assert.equal(await count(page), 1)
  await page.getByRole('button', { name: 'Clear history', exact: true }).click()
  await page.getByRole('button', { name: 'Delete all meals' }).click()
  assert.equal(await count(page), 0)
  scenario = 'unknown'
  await upload(page)
  await waitText(page.getByLabel('Current meal totals', { exact: true }), 'Incomplete estimate')
  await page.getByRole('button', { name: 'Save meal', exact: true }).click()
  await waitText(page.locator('.daily-summary'), 'Daily totals are incomplete')
  await page.getByRole('checkbox', { name: 'Include Idli', exact: true }).uncheck()
  assert.match(await page.getByLabel('Current meal totals', { exact: true }).innerText(), /Totals are unknown/)
  await page.getByRole('checkbox', { name: 'Include Unknown dish' }).uncheck()
  assert.equal(await page.getByRole('button', { name: 'Update saved meal' }).isDisabled(), true)
  await page.getByRole('checkbox', { name: 'Include Idli', exact: true }).check()
  await page.getByRole('button', { name: 'Update saved meal' }).click()
  assert.equal((await read(page)).meals.length, 1)
  assert.equal(await page.locator('.daily-summary').getByText('Daily totals are incomplete.').count(), 0)
  // Storage write failures must not claim the change was saved.
  await page.evaluate(() => { Storage.prototype.setItem = () => { throw new DOMException('Quota exceeded', 'QuotaExceededError') } })
  await page.getByRole('button', { name: 'Increase Idli portion' }).click()
  await page.getByRole('button', { name: 'Update saved meal' }).click()
  await page.getByRole('alert').filter({ hasText: 'Changes could not be saved' }).waitFor()
  assert.equal((await read(page)).meals[0].items[0].grams, 100)
  await context.close()

  for (const raw of ['{broken', '{"version":99}']) {
    scenario = 'success'
    const { page, context } = await setup()
    await page.addInitScript(({ key, raw }) => localStorage.setItem(key, raw), { key, raw })
    await page.goto(url)
    await page.getByRole('alert').filter({ hasText: 'Saving is paused' }).waitFor()
    await upload(page); await page.getByRole('button', { name: 'Save meal', exact: true }).click()
    assert.equal(await page.evaluate(key => localStorage.getItem(key), key), raw)
    assert.equal(await count(page), 0)
    await context.close()
  }
  {
    const { page, context } = await setup()
    await page.addInitScript(() => { Storage.prototype.getItem = () => { throw new DOMException('Storage blocked', 'SecurityError') } })
    await page.goto(url); await page.getByRole('alert').filter({ hasText: 'Saving is paused' }).waitFor()
    await upload(page)
    await context.close()
  }
  // Midnight updates saved-day totals without changing historical records.
  {
    const { page, context } = await setup()
    await page.clock.install({ time: new Date(2026, 8, 11, 23, 59, 50) })
    await page.goto(url); await upload(page)
    await page.getByRole('button', { name: 'Save meal', exact: true }).click()
    assert.match(await page.locator('.daily-number').innerText(), /^100/)
    await page.clock.fastForward(15000)
    await waitText(page.locator('.daily-number'), '0')
    assert.match(await page.locator('.daily-number').innerText(), /^0/)
    assert.equal(await count(page), 1)
    await context.close()
  }
  {
    scenario = 'advice-failure'
    const { page, context } = await setup({ viewport: { width: 360, height: 800 }, reducedMotion: 'reduce' })
    await page.goto(url)
    const scanBox = await page.locator('#scan').boundingBox(), summaryBox = await page.locator('.daily-summary').boundingBox()
    assert(summaryBox.y > scanBox.y)
    await page.screenshot({ path: '.deployment/food-first-mobile.png', fullPage: true })
    await upload(page)
    await page.getByRole('alert').filter({ hasText: 'Guidance unavailable' }).waitFor()
    await page.getByRole('button', { name: 'Save meal', exact: true }).click()
    assert.equal(await count(page), 1)
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true)
    await page.screenshot({ path: '.deployment/food-first-mobile-results.png', fullPage: true })
    await context.close()
  }
  assert.deepEqual(errors, [])
  console.log('PASS: journal save/update, persistence, editing, deletion/undo, clearing, unknown nutrition, exclusions, privacy, storage failures, midnight, mobile, keyboard upload, guidance isolation')
} finally { await browser.close() }
