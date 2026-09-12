import assert from 'node:assert/strict'
import { launchBrowser, mockMacros } from './browser_support.mjs'

const browser = await launchBrowser()
try {
  for (const width of [1280, 360]) {
    const context = await browser.newContext({ viewport: { width, height: 900 }, reducedMotion: 'reduce' })
    const page = await context.newPage()
    const errors = []
    page.on('pageerror', error => errors.push(error.message))
    let requests = 0, analysisRequests = 0, scenario = 'none', finishAnalysis, onAnalysisStarted
    await page.route('**/api/**', async route => {
      requests++
      const path = new URL(route.request().url()).pathname
      let body = {}
      if (path.endsWith('/goals')) body = { goals: [] }
      if (path.endsWith('/health-conditions')) body = { health_conditions: [] }
      if (path.endsWith('/calculate-macros')) body = mockMacros(route.request().postDataJSON())
      if (path.endsWith('/recommendations')) body = { recommendations: ['One', 'Two', 'Three'], source: 'fallback', health_condition: 'none' }
      if (path.endsWith('/analyze-food')) {
        analysisRequests++
        await new Promise(resolve => { finishAnalysis = resolve; onAnalysisStarted() })
        body = { detections: scenario === 'none' ? [] : [{ food_label: 'idli', display_name: 'Idli', confidence: .9, bounding_box: [10, 10, 80, 80], macros: null, macros_unit: 'per_100g', nutrition_source: null }], food_not_found: scenario === 'none', img_width: 100, img_height: 100 }
      }
      await route.fulfill({ contentType: 'application/json', body: JSON.stringify(body) })
    })
    await page.goto('http://127.0.0.1:4173')
    assert.equal(await page.title(), 'AI Food Recognition | Nutrition-Aware Recommendations')
    await page.waitForLoadState('networkidle')
    const catalog = page.locator('.supported-foods')
    const summary = catalog.locator('summary')
    const search = page.getByRole('searchbox', { name: 'Search supported foods' })
    const count = catalog.getByRole('status')
    assert.equal(await catalog.locator('details').evaluate(element => element.open), false)
    const notice = await catalog.getByText('Trained to recognize 72 food categories.', { exact: true }).boundingBox()
    const choose = await page.getByRole('button', { name: 'Choose Image', exact: true }).boundingBox()
    assert(notice.y < choose.y, 'notice must precede upload controls')
    const beforeBrowse = requests
    await summary.focus()
    await page.keyboard.press('Enter')
    await page.keyboard.press('Tab')
    assert(await search.evaluate(element => element === document.activeElement))
    const names = await catalog.locator('li').allTextContents()
    assert.equal(names.length, 72)
    assert.deepEqual(names, [...names].sort((a, b) => a.localeCompare(b, 'en')))
    for (const query of ['idli', 'Palak Paneer', 'palak_paneer', 'PALAK-PANEER']) {
      await search.fill(query)
      await count.filter({ hasText: '1 of 72 categories' }).waitFor()
      assert.equal(await catalog.locator('li').innerText(), query === 'idli' ? 'Idli' : 'Palak Paneer')
    }
    await search.fill('pizza')
    await catalog.getByText('No supported categories match your search.', { exact: false }).waitFor()
    assert.equal(await count.innerText(), '0 of 72 categories')
    await page.keyboard.press('Tab')
    assert(await catalog.getByRole('button', { name: 'Clear search' }).evaluate(element => element === document.activeElement))
    await page.keyboard.press('Enter')
    assert(await search.evaluate(element => element === document.activeElement))
    assert.equal(await catalog.locator('li').count(), 72)
    assert.equal(requests, beforeBrowse, 'browsing must make no API calls')
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true)
    assert.equal(await page.evaluate(() => getComputedStyle(document.documentElement).scrollBehavior), 'auto')
    await page.screenshot({ path: `screenshots/supported-foods-${width}.png`, fullPage: true })

    const png = await page.evaluate(() => { const canvas = document.createElement('canvas'); canvas.width = canvas.height = 100; canvas.getContext('2d').fillRect(0, 0, 100, 100); return canvas.toDataURL().split(',')[1] })
    const upload = () => page.locator('input[type=file]').setInputFiles({ name: 'food.png', mimeType: 'image/png', buffer: Buffer.from(png, 'base64') })
    const started = new Promise(resolve => { onAnalysisStarted = resolve })
    await upload()
    await started
    await search.fill('idli')
    await count.filter({ hasText: '1 of 72 categories' }).waitFor()
    const preview = page.locator('#scan img')
    const previewUrl = await preview.getAttribute('src')
    assert.equal(analysisRequests, 1)
    await summary.click()
    assert.equal(await catalog.locator('details').evaluate(element => element.open), false)
    finishAnalysis()
    const empty = page.getByRole('status').filter({ hasText: 'No supported food was detected in this photo.' })
    await empty.waitFor()
    assert.equal(await preview.getAttribute('src'), previewUrl)
    assert.equal(await catalog.getByText('Trained to recognize 72 food categories.', { exact: true }).isVisible(), true)
    const beforeReopen = requests
    await page.getByRole('button', { name: 'View supported foods', exact: true }).click()
    assert(await search.evaluate(element => element === document.activeElement))
    assert.equal(await search.inputValue(), '')
    assert.equal(await catalog.locator('li').count(), 72)
    assert.equal(await preview.getAttribute('src'), previewUrl)
    assert.equal(requests, beforeReopen)
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true)
    await page.getByRole('button', { name: 'Choose another image' }).click()
    assert.equal(await preview.count(), 0)
    assert.equal(await empty.count(), 0)
    assert.equal(await page.getByRole('button', { name: 'View supported foods', exact: true }).count(), 0)

    scenario = 'success'
    const nextStarted = new Promise(resolve => { onAnalysisStarted = resolve })
    await upload()
    await nextStarted
    finishAnalysis()
    await page.getByText('Other foods in the photo may not have been recognized.', { exact: true }).waitFor()
    assert.equal(await empty.count(), 0)
    assert.equal(await page.getByRole('button', { name: 'View supported foods', exact: true }).count(), 0)
    assert.deepEqual(errors, [])
    await context.close()
  }
  console.log('PASS: supported-food catalog, local search, keyboard/mobile, in-flight browsing, empty-result focus, preview/reset, and partial-recognition notice')
} finally { await browser.close() }
