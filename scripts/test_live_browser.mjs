import assert from 'node:assert/strict'
import { chromium } from '../.deployment/browser-tools/node_modules/playwright/index.mjs'

const browser = await chromium.launch({ channel: 'msedge', headless: true })
try {
  const page = await browser.newPage()
  const pageErrors = []
  page.on('pageerror', error => pageErrors.push(error.message))
  await page.goto('https://food-recognition-nutrition.vercel.app', { waitUntil: 'networkidle' })
  const advice = page.waitForResponse(response => response.url().endsWith('/api/recommendations'), { timeout: 120000 })
  await page.locator('input[type=file]').setInputFiles('data/food_dataset/valid/images/valid2282-aloo_gobi.jpg')
  const response = await advice
  assert.equal(response.status(), 200)
  const result = await response.json()
  assert.equal(result.source, 'groq')
  assert.equal(result.recommendations.length, 3)
  await page.getByText('Detected 1 Food Item', { exact: true }).waitFor()
  assert.deepEqual(pageErrors, [])
  await page.screenshot({ path: '.deployment/live-site.png', fullPage: true })
  console.log('PASS: public browser upload, food detection, nutrition display, and Groq advice; no browser exceptions')
} finally {
  await browser.close()
}
