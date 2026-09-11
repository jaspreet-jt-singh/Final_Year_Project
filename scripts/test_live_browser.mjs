import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import { chromium } from '../.deployment/browser-tools/node_modules/playwright/index.mjs'

const browser = await chromium.launch({ channel: 'msedge', headless: true })
try {
  const url = process.argv[2] || 'https://food-recognition-nutrition.vercel.app'
  const page = await browser.newPage()
  if (process.argv.includes('--protected')) {
    const host = new URL(url).hostname
    assert(host.startsWith('food-recognition-nutrition-') && host.endsWith('-jaspreet-jt-singh.vercel.app'))
    const result = spawnSync('npx.cmd', ['--yes', 'vercel@latest', 'api', '/v9/projects/food-recognition-nutrition', '--scope', 'jaspreet-jt-singh'], { encoding: 'utf8', shell: true })
    assert.equal(result.status, 0, 'Could not load project bypass for preview')
    const project = JSON.parse(result.stdout)
    const token = Object.entries(project.protectionBypass).find(([, value]) => value.scope === 'automation-bypass')[0]
    await page.route(`${new URL(url).origin}/**`, route => route.continue({ headers: { ...route.request().headers(), 'x-vercel-protection-bypass': token } }))
  }
  const pageErrors = []
  page.on('pageerror', error => pageErrors.push(error.message))
  await page.goto(url, { waitUntil: 'networkidle' })
  const advice = page.waitForResponse(response => response.url().endsWith('/api/recommendations'), { timeout: 120000 })
  await page.locator('input[type=file]').setInputFiles('data/food_dataset/valid/images/valid2282-aloo_gobi.jpg')
  const response = await advice
  assert.equal(response.status(), 200)
  const result = await response.json()
  assert.equal(result.source, 'groq')
  assert.equal(result.recommendations.length, 3)
  await page.getByText('Detected 1 Food Item. Review portions before saving.', { exact: true }).waitFor()
  assert.equal(await page.locator('#history article').count(), 0)
  await page.getByRole('button', { name: /^Increase .* portion$/ }).first().click()
  await page.getByRole('button', { name: 'Save meal', exact: true }).click()
  await page.getByRole('button', { name: 'Meal saved', exact: true }).waitFor()
  assert.equal(await page.locator('#history article').count(), 1)
  await page.reload({ waitUntil: 'networkidle' })
  await page.locator('#history article').waitFor()
  assert.equal(await page.locator('#history article').count(), 1)
  assert.deepEqual(pageErrors, [])
  await page.screenshot({ path: '.deployment/food-first-live.png', fullPage: true })
  console.log('PASS: real browser upload, food detection, Groq advice, portion editing, save and reload persistence; no browser exceptions')
} finally {
  await browser.close()
}
