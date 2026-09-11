import assert from 'node:assert/strict'
import { launchBrowser, mockMacros } from './browser_support.mjs'

const browser = await launchBrowser()
try {
  const page = await browser.newPage({ viewport: { width: 360, height: 800 } })
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  let mode = 'normal'
  let resolveSlow
  let adviceCalls = 0
  const food = { food_label: 'Idli', display_name: 'Idli', confidence: .9, bounding_box: [10, 10, 80, 80], macros: { calories: 100, protein_g: 3, carbs_g: 20, fat_g: 1 }, macros_unit: 'per_100g', nutrition_source: 'INDB' }
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname
    let status = 200, body = {}
    if (path.endsWith('/goals')) body = { goals: [] }
    if (path.endsWith('/health-conditions')) body = { health_conditions: [] }
    if (path.endsWith('/calculate-macros')) body = mockMacros(route.request().postDataJSON())
    if (path.endsWith('/analyze-food')) body = { detections: [food], img_width: 100, img_height: 100, food_not_found: false }
    if (path.endsWith('/recommendations')) {
      adviceCalls++
      const { health_condition: condition } = route.request().postDataJSON()
      if (mode === 'slow' && condition === 'diabetic') await new Promise(resolve => { resolveSlow = resolve })
      body = { recommendations: [`Advice for ${condition}`, 'Two', 'Three'], source: mode === 'fallback' ? 'fallback' : 'groq', health_condition: condition }
      if (mode === 'mismatch') body.health_condition = 'diabetic'
      if (mode === 'missing') delete body.health_condition
      if (mode === 'error') { status = 503; body = { detail: 'Provider busy' } }
    }
    await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) }).catch(() => {})
  })
  await page.goto('http://127.0.0.1:4173')
  const png = await page.evaluate(() => { const canvas = document.createElement('canvas'); canvas.width = canvas.height = 100; return canvas.toDataURL().split(',')[1] })
  await page.locator('input[type=file]').setInputFiles({ name: 'food.png', mimeType: 'image/png', buffer: Buffer.from(png, 'base64') })
  await page.getByText('General nutrition guidance', { exact: true }).waitFor()
  await page.getByText('Goals & advanced settings', { exact: true }).click()
  const select = page.getByLabel('Health context (this session only)')
  await select.selectOption('diabetic')
  await page.getByText('Updating for diabetes…', { exact: true }).waitFor()
  assert.equal(await page.getByText('General nutrition guidance', { exact: true }).count(), 0)
  await page.getByText('Adjusted for diabetes', { exact: true }).waitFor()
  mode = 'fallback'
  await select.selectOption('hypertension')
  await page.getByText('Adjusted for high blood pressure', { exact: true }).waitFor()
  await page.getByText('Local fallback suggestions', { exact: false }).waitFor()
  mode = 'slow'
  const request = page.waitForRequest(request => request.url().endsWith('/recommendations') && request.postDataJSON().health_condition === 'diabetic')
  await select.selectOption('diabetic'); await request
  while (!resolveSlow) await page.waitForTimeout(10)
  await select.selectOption('hypertension')
  await page.getByText('Adjusted for high blood pressure', { exact: true }).waitFor()
  resolveSlow(); await page.waitForTimeout(150)
  assert.equal(await page.getByText('Adjusted for diabetes', { exact: true }).count(), 0)
  assert.equal(await page.getByText('Advice for diabetic', { exact: true }).count(), 0)
  for (const failure of ['missing', 'mismatch', 'error']) {
    mode = failure
    await select.selectOption('none')
    await page.getByRole('alert').filter({ hasText: failure === 'error' ? 'Provider busy' : 'invalid response' }).waitFor()
    assert.equal(await page.locator('.guidance .pill').count(), 0)
    mode = 'normal'
    await page.getByRole('button', { name: 'Retry guidance' }).click()
    await page.getByText('General nutrition guidance', { exact: true }).waitFor()
    await select.selectOption('hypertension')
    await page.getByText('Adjusted for high blood pressure', { exact: true }).waitFor()
  }
  mode = 'normal'
  await select.selectOption('none')
  await page.getByText('General nutrition guidance', { exact: true }).waitFor()
  const before = adviceCalls
  await page.getByRole('button', { name: 'Increase Idli portion' }).click()
  await page.waitForTimeout(500)
  assert.equal(adviceCalls, before)
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true)
  assert.deepEqual(errors, [])
  console.log('PASS: health badges, immediate loading state, stale response suppression, mismatched/missing context, errors, fallback labeling, retry and mobile layout')
} finally { await browser.close() }
