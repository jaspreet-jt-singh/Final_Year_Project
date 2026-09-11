import assert from 'node:assert/strict'
import { chromium } from '../.deployment/browser-tools/node_modules/playwright/index.mjs'

const browser = await chromium.launch({ channel: 'msedge', headless: true })
try {
  const page = await browser.newPage()
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  let scenario = 'success'
  let uploadedBytes = 0
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname
    let status = 200
    let body = {}
    if (path.endsWith('/goals')) body = { goals: [] }
    if (path.endsWith('/health-conditions')) body = { health_conditions: [] }
    if (path.endsWith('/calculate-macros')) body = { target_calories: 2000, carbs_g: 250, protein_g: 125, fat_g: 56 }
    if (path.endsWith('/recommendations')) body = { recommendations: ['One', 'Two', 'Three'], source: 'fallback' }
    if (path.endsWith('/analyze-food')) {
      uploadedBytes = route.request().postDataBuffer().length
      if (scenario === 'success') body = {
        detections: [{ food_label: 'Idli', display_name: 'Idli', confidence: 0.9,
          bounding_box: [160, 100, 800, 500], macros: { calories: 100, protein_g: 3, carbs_g: 20, fat_g: 1 },
          macros_unit: 'per_100g', nutrition_source: 'INDB' }],
        img_width: 1600, img_height: 1067, food_not_found: false,
      }
      if (scenario === 'limited') { status = 429; body = { message: 'Rate limit' } }
      if (scenario === 'invalid') { status = 400; body = { detail: 'Invalid image from server' } }
      if (scenario === 'busy') { status = 503; body = { detail: 'Analyzer is busy. Please retry shortly.' } }
      if (scenario === 'none') body = { detections: [], food_not_found: true, img_width: null, img_height: null }
    }
    await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) })
  })
  await page.goto('http://127.0.0.1:4173')
  const png = await page.evaluate(() => {
    const canvas = document.createElement('canvas')
    canvas.width = 3000
    canvas.height = 2000
    canvas.getContext('2d').fillRect(0, 0, 3000, 2000)
    return canvas.toDataURL('image/png').split(',')[1]
  })
  const upload = () => page.locator('input[type=file]').setInputFiles({ name: 'large.png', mimeType: 'image/png', buffer: Buffer.from(png, 'base64') })
  await upload()
  await page.getByText('Detected 1 Food Item. Review portions before saving.', { exact: true }).waitFor()
  await page.getByText('View detection image & confidence', { exact: true }).click()
  const size = await page.getByAltText('Detected foods').evaluate(img => [img.naturalWidth, img.naturalHeight])
  assert.deepEqual(size, [1600, 1067])
  assert(uploadedBytes < 4.5 * 1000000)
  assert.equal(await page.locator('.pointer-events-none').first().evaluate(el => el.style.left), '10%')
  for (const [name, message] of [['limited', 'Too many requests. Please wait a minute and try again.'], ['invalid', 'Invalid image from server'], ['busy', 'Analyzer is busy. Please retry shortly.'], ['none', 'No food detected in this image.']]) {
    scenario = name
    await page.getByRole('button', { name: 'Choose another image' }).click()
    await upload()
    await page.getByText(message, { exact: true }).waitFor()
    if (name !== 'none') assert.equal(await page.getByText('No food detected in this image.', { exact: true }).count(), 0)
  }
  await page.getByRole('button', { name: 'Choose another image' }).click()
  await page.locator('input[type=file]').setInputFiles({ name: 'too-large.jpg', mimeType: 'image/jpeg', buffer: Buffer.alloc(26 * 1024 * 1024) })
  await page.getByRole('alert').filter({ hasText: 'smaller than 25 MiB' }).waitFor()
  await page.locator('input[type=file]').setInputFiles({ name: 'bad.jpg', mimeType: 'image/jpeg', buffer: Buffer.from('invalid-image') })
  await page.getByRole('alert').filter({ hasText: 'could not be opened' }).waitFor()
  assert.deepEqual(errors, [])
  console.log('PASS: resized uploads, aligned overlay, visible 400/429 errors, no-food result, no browser exceptions')
} finally {
  await browser.close()
}
