/** Additional offline browser evidence. Start a static frontend/out server first.
 * No live API/provider requests: all APIs are intercepted and external URLs blocked.
 * Usage: node scripts/test_validation_browser.mjs --run-id validation-2026-09-12-v1
 */
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { parseArgs } from 'node:util'
import { launchBrowser, mockMacros } from './browser_support.mjs'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const { values } = parseArgs({ options: { ci: { type: 'boolean', default: false }, 'run-id': { type: 'string' }, 'report-name': { type: 'string', default: 'browser-extended.json' } } })
const ci = values.ci
const runId = values['run-id']
const reportName = values['report-name']
if (ci) assert.equal(runId, undefined, '--ci cannot claim a frozen audit run')
else assert.match(runId || '', /^validation-[a-z0-9-]+$/)
assert.match(reportName, /^browser-extended(?:-[a-z0-9-]+)?\.json$/)
const reportDir = ci ? null : path.join(root, 'research/evidence', runId)
const localDir = ci ? null : path.join(root, '.deployment/research', runId)
const targets = ci ? [] : [path.join(reportDir, reportName), path.join(localDir, reportName)]
assert(targets.every(target => !fs.existsSync(target)), 'Refusing to overwrite an existing browser receipt')
if (!ci) assert(fs.statSync(localDir).isDirectory(), 'Frozen local baseline required')
const sha = bytes => createHash('sha256').update(bytes).digest('hex')
const baselineBytes = ci ? null : fs.readFileSync(path.join(reportDir, 'baseline.json'))
const baseline = ci ? { files: [], source_commit: null } : JSON.parse(baselineBytes)
if (!ci) assert.equal(baseline.run_id, runId)
const policy = JSON.parse(fs.readFileSync(path.join(root, 'backend/domain/nutrition_policy.json')))
const conditionEntries = Object.entries(policy.conditions)
const goalEntries = Object.entries(policy.goals)
assert.equal(conditionEntries.length, 9)
assert.equal(goalEntries.length, 4)
const url = 'http://127.0.0.1:4173'
const storageKey = 'food-recognition.journal'
const fixtureFood = (name, macros = { calories: 123, protein_g: 4, carbs_g: 20, fat_g: 3 }) => ({
  food_label: name.replaceAll(' ', '_'), display_name: name, confidence: .9,
  bounding_box: [10, 10, 80, 80], macros, macros_unit: 'per_100g',
  nutrition_source: macros ? 'Synthetic fixture only' : null,
})
const fixtures = {
  pair: [fixtureFood('Synthetic A'), fixtureFood('Synthetic B')],
  replacement: [fixtureFood('Synthetic Replacement')],
  unknown: [fixtureFood('Synthetic Unknown', null)],
}
const testedPaths = [
  'frontend/lib/useRecommendations.ts', 'frontend/lib/endpoints.ts', 'frontend/lib/api.ts',
  'frontend/lib/useGoalSettings.ts', 'frontend/lib/useJournal.ts', 'frontend/lib/journalStorage.ts',
  'frontend/lib/meals.ts', 'frontend/lib/generated/nutritionPolicy.ts',
  'frontend/components/RecommendationPanel.tsx', 'frontend/components/GoalSettings.tsx',
  'frontend/components/MealItems.tsx', 'frontend/components/DailySummary.tsx',
  'frontend/components/ImageUpload.tsx', 'frontend/package-lock.json', 'scripts/browser_support.mjs',
  'backend/domain/nutrition_policy.json',
]
const inputIdentity = testedPaths.map(name => {
  const hash = sha(fs.readFileSync(path.join(root, name)))
  const recorded = baseline.files.find(entry => entry.path === name)?.sha256
  return { path: name, sha256: hash, baseline_sha256: recorded ?? null, matches_baseline: ci ? null : hash === recorded }
})
const started = performance.now()
const report = {
  schema_version: 1, run_id: runId ?? null, mode: ci ? 'ci-ephemeral' : 'frozen-audit', started_at_utc: new Date().toISOString(),
  command: [process.execPath, ...process.argv.slice(1)], baseline_sha256: baselineBytes ? sha(baselineBytes) : null,
  source_commit: baseline.source_commit, runtime_inputs: inputIdentity,
  validator: { path: 'scripts/test_validation_browser.mjs', sha256: sha(fs.readFileSync(fileURLToPath(import.meta.url))) },
  fixture_identity: { version: 'synthetic-browser-v1', sha256: sha(JSON.stringify(fixtures)), fixtures,
    description: 'Invented food names/macros and canvas PNG; intercepted responses are not real inference or clinical advice.' },
  environment: { node: process.version, platform: process.platform, architecture: process.arch,
    playwright: JSON.parse(fs.readFileSync(path.join(root, 'frontend/node_modules/playwright/package.json'))).version,
    browser_channel: process.env.BROWSER_CHANNEL || 'bundled-chromium' },
  static_export_index_sha256: sha(fs.readFileSync(path.join(root, 'frontend/out/index.html'))),
  cases: [], matrix: [], page_errors: [], unexpected_network: [],
  boundaries: { live_provider_calls: 0, live_inference_calls: 0, external_network_allowed: false,
    clinical_validity_established: false, production_deployment_validated: false },
  retained_regressions: [
    { script: 'scripts/test_journal_browser.mjs', coverage: 'Midnight timer, corrupt/unsupported/blocked/quota storage, portion edits, deletion/undo, clearing, keyboard upload, scan/save separation.' },
    { script: 'scripts/test_frontend.mjs', coverage: 'Upload preparation/orientation, boxes, empty/invalid responses, request timeout/rate errors.' },
    { script: 'scripts/test_health_browser.mjs', coverage: 'Missing/mismatched context, explicit retry, fallback labels, portion-only non-refetch and standard abort race.' },
  ].map(row => ({ ...row, sha256: sha(fs.readFileSync(path.join(root, row.script))), executed_by_this_script: false })),
}

let browser
const openHarnesses = []
async function check(id, fn) {
  const tick = performance.now()
  try {
    const details = await fn()
    report.cases.push({ id, status: 'pass', duration_seconds: (performance.now() - tick) / 1000, ...details })
    console.log(`PASS: ${id}`)
  } catch (error) {
    report.cases.push({ id, status: 'fail', duration_seconds: (performance.now() - tick) / 1000, error: error.message })
    throw error
  }
}

async function until(test, message) {
  const deadline = performance.now() + 8000
  while (!test()) {
    assert(performance.now() < deadline, message)
    await new Promise(resolve => setTimeout(resolve, 10))
  }
}

async function harness({ lateResponses = false, mobile = false, foods = fixtures.pair } = {}) {
  const context = await browser.newContext({ viewport: mobile ? { width: 360, height: 800 } : { width: 1280, height: 900 }, timezoneId: 'Asia/Kolkata', reducedMotion: 'reduce' })
  const page = await context.newPage()
  page.setDefaultTimeout(8000)
  const state = { context, page, foods, calls: [], held: [], holdNext: 0, delivered: [] }
  openHarnesses.push(state)
  page.on('pageerror', error => report.page_errors.push(error.message))
  if (lateResponses) {
    // Deliberately make only recommendation fetch ignore network cancellation.
    // The real hook still aborts its controller. This proves stale suppression
    // when superseded responses actually arrive, not merely when HTTP is aborted.
    await page.addInitScript(() => {
      const original = window.fetch.bind(window)
      window.fetch = (input, options = {}) => {
        const target = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url
        return original(input, target.includes('/api/recommendations') ? { ...options, signal: undefined } : options)
      }
    })
  }
  await context.route('**/*', async route => {
    const target = new URL(route.request().url())
    if (target.origin !== url) {
      report.unexpected_network.push({ origin: target.origin, path: target.pathname })
      await route.abort()
      return
    }
    if (!target.pathname.startsWith('/api/')) { await route.continue(); return }
    let body
    if (target.pathname === '/api/user/goals') body = { goals: [] }
    else if (target.pathname === '/api/user/health-conditions') body = { health_conditions: [] }
    else if (target.pathname === '/api/user/calculate-macros') body = mockMacros(route.request().postDataJSON())
    else if (target.pathname === '/api/analyze-food') body = { detections: state.foods, img_width: 100, img_height: 100, food_not_found: false }
    else if (target.pathname === '/api/recommendations') {
      const input = route.request().postDataJSON()
      const id = state.calls.length + 1
      const marker = `Synthetic response ${id}: ${input.user_goal} | ${input.health_condition} | ${input.detected_foods.map(food => food.display_name).join(', ')}`
      const conditionIndex = conditionEntries.findIndex(([key]) => key === input.health_condition)
      body = { recommendations: [marker, 'Synthetic second point; no medical assertion.', 'Synthetic third point; no medical assertion.'], source: conditionIndex % 2 ? 'groq' : 'fallback', health_condition: input.health_condition }
      const call = { id, goal: input.user_goal, condition: input.health_condition, names: input.detected_foods.map(food => food.display_name), marker, source: body.source }
      state.calls.push(call)
      if (state.holdNext > 0) {
        state.holdNext--
        await new Promise(resolve => state.held.push({ ...call, release: resolve }))
      }
      try {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) })
        state.delivered.push(id)
      } catch { /* Normal cancellation is allowed; late-response fixtures disable it. */ }
      return
    } else {
      report.unexpected_network.push({ origin: target.origin, path: target.pathname, reason: 'unmocked_api' })
      await route.abort()
      return
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) })
  })
  return state
}

async function upload(state) {
  const { page } = state
  const png = await page.evaluate(() => {
    const canvas = document.createElement('canvas'); canvas.width = canvas.height = 100
    canvas.getContext('2d').fillRect(10, 10, 70, 70)
    return canvas.toDataURL('image/png').split(',')[1]
  })
  report.fixture_identity.processed_input_png_sha256 = sha(Buffer.from(png, 'base64'))
  await page.getByLabel('Choose food image').setInputFiles({ name: 'synthetic.png', mimeType: 'image/png', buffer: Buffer.from(png, 'base64') })
  await page.getByRole('button', { name: 'Save meal', exact: true }).waitFor()
}

async function waitAdvice(state, goal, condition, names) {
  const deadline = performance.now() + 8000
  let call
  while (true) {
    call = state.calls.findLast(call => call.goal === goal && call.condition === condition && JSON.stringify(call.names) === JSON.stringify(names))
    if (call && await state.page.getByText(call.marker, { exact: true }).isVisible()) break
    assert(performance.now() < deadline, `Expected visible advice for ${goal}/${condition}/${names.join(',')}`)
    await new Promise(resolve => setTimeout(resolve, 10))
  }
  await state.page.locator('.guidance [role=status]').getByText(policy.conditions[condition].adjustment_label, { exact: true }).waitFor()
  return call
}

async function goal(state, name) {
  await state.page.getByLabel('Your goal').selectOption(name)
  await state.page.getByRole('button', { name: 'Save goals', exact: true }).click()
}

async function releaseAndCheck(state, old, current) {
  old.release()
  await until(() => state.delivered.includes(old.id), 'Older response must actually be delivered in late-response fixture')
  await state.page.waitForTimeout(120)
  assert.equal(await state.page.getByText(old.marker, { exact: true }).count(), 0)
  await state.page.getByText(current.marker, { exact: true }).waitFor()
}

try {
  if (!ci) assert(inputIdentity.every(input => input.matches_baseline), 'Runtime source drifted from frozen baseline')
  browser = await launchBrowser()
  report.environment.browser = browser.version()
  await check('all_36_goal_context_badges_and_sources', async () => {
    const state = await harness()
    await state.page.goto(url)
    await upload(state)
    await waitAdvice(state, 'Maintenance', 'none', ['Synthetic A', 'Synthetic B'])
    await state.page.getByText('Goals & advanced settings', { exact: true }).click()
    for (const [goalKey, goalOption] of goalEntries) {
      await goal(state, goalOption.name)
      for (const [conditionKey, condition] of conditionEntries) {
        const tick = performance.now()
        await state.page.getByLabel('Health context (this session only)').selectOption(conditionKey)
        const call = await waitAdvice(state, goalOption.name, conditionKey, ['Synthetic A', 'Synthetic B'])
        const sourceLabel = call.source === 'fallback' ? 'Local fallback suggestions' : 'AI-generated suggestions'
        await state.page.locator('.guidance').getByText(sourceLabel, { exact: false }).waitFor()
        assert.equal(await state.page.locator('.guidance .pill').count(), 1)
        assert.match(await state.page.locator('.daily-number').innerText(), /^0/)
        assert.equal(await state.page.locator('#history article').count(), 0)
        report.matrix.push({ goal: goalKey, context: conditionKey, adjustment_label: condition.adjustment_label, source: call.source, status: 'pass', duration_seconds: (performance.now() - tick) / 1000 })
      }
    }
    assert.equal(new Set(report.matrix.map(row => `${row.goal}/${row.context}`)).size, 36)
    await state.context.close()
    return { combinations: 36, scan_did_not_change_saved_totals: true, live_provider_calls: 0 }
  })

  const race = await harness({ lateResponses: true })
  await race.page.goto(url)
  await upload(race)
  await waitAdvice(race, 'Maintenance', 'none', ['Synthetic A', 'Synthetic B'])
  await race.page.getByText('Goals & advanced settings', { exact: true }).click()

  await check('context_supersession_delivered_reverse_order', async () => {
    race.holdNext = 1
    await race.page.getByLabel('Health context (this session only)').selectOption('diabetic')
    await until(() => race.held.length === 1, 'Held diabetic request')
    const old = race.held.at(-1)
    await race.page.getByLabel('Health context (this session only)').selectOption('hypertension')
    assert.equal(await race.page.locator('.guidance .pill').count(), 0)
    await race.page.getByRole('status').filter({ hasText: 'Updating for high blood pressure' }).waitFor()
    const current = await waitAdvice(race, 'Maintenance', 'hypertension', ['Synthetic A', 'Synthetic B'])
    await releaseAndCheck(race, old, current)
    return { network_abort_deliberately_ignored: true, old_response_delivered_after_new: true }
  })

  await check('goal_supersession_delivered_reverse_order', async () => {
    race.holdNext = 1
    const before = race.held.length
    await goal(race, 'Weight Loss')
    await until(() => race.held.length === before + 1, 'Held old-goal request')
    const old = race.held.at(-1)
    await goal(race, 'Muscle Gain')
    assert.equal(await race.page.locator('.guidance .pill').count(), 0)
    const current = await waitAdvice(race, 'Muscle Gain', 'hypertension', ['Synthetic A', 'Synthetic B'])
    await releaseAndCheck(race, old, current)
    return { network_abort_deliberately_ignored: true }
  })

  await check('included_food_supersession_delivered_reverse_order', async () => {
    race.holdNext = 1
    const before = race.held.length
    await race.page.getByRole('checkbox', { name: 'Include Synthetic B', exact: true }).uncheck()
    await until(() => race.held.length === before + 1, 'Held old-food request')
    const old = race.held.at(-1)
    await race.page.getByRole('checkbox', { name: 'Include Synthetic B', exact: true }).check()
    const current = await waitAdvice(race, 'Muscle Gain', 'hypertension', ['Synthetic A', 'Synthetic B'])
    await releaseAndCheck(race, old, current)
    return { network_abort_deliberately_ignored: true }
  })

  await check('three_superseded_context_goal_food_responses_released_reverse_order', async () => {
    race.holdNext = 3
    const before = race.held.length
    await race.page.getByLabel('Health context (this session only)').selectOption('thyroid')
    await until(() => race.held.length === before + 1, 'Held first request')
    await goal(race, 'Endurance')
    await until(() => race.held.length === before + 2, 'Held second request')
    await race.page.getByRole('checkbox', { name: 'Include Synthetic B', exact: true }).uncheck()
    await until(() => race.held.length === before + 3, 'Held third request')
    await race.page.getByLabel('Health context (this session only)').selectOption('none')
    const current = await waitAdvice(race, 'Endurance', 'none', ['Synthetic A'])
    for (const old of race.held.slice(before).reverse()) await releaseAndCheck(race, old, current)
    return { reversed_late_responses: 3, network_abort_deliberately_ignored: true }
  })

  await check('all_excluded_cancels_pending_and_sends_no_empty_food_request', async () => {
    race.holdNext = 1
    const heldBefore = race.held.length
    await race.page.getByLabel('Health context (this session only)').selectOption('diabetic')
    await until(() => race.held.length === heldBefore + 1, 'Held advice before excluding all foods')
    const pending = race.held.at(-1)
    const before = race.calls.length
    await race.page.getByRole('checkbox', { name: 'Include Synthetic A', exact: true }).uncheck()
    await race.page.getByText('Include a food to see suggestions.', { exact: true }).waitFor()
    assert.equal(await race.page.getByRole('button', { name: 'Save meal', exact: true }).isDisabled(), true)
    pending.release()
    await until(() => race.delivered.includes(pending.id), 'Late advice after all foods excluded must actually arrive')
    await race.page.getByLabel('Health context (this session only)').selectOption('none')
    await race.page.waitForTimeout(650)
    assert.equal(race.calls.length, before)
    assert.equal(await race.page.getByText(pending.marker, { exact: true }).count(), 0)
    await race.page.getByText('Include a food to see suggestions.', { exact: true }).waitFor()
    assert.equal(await race.page.locator('.guidance .pill').count(), 0)
    assert(race.calls.every(call => call.names.length > 0))
    await race.page.getByRole('checkbox', { name: 'Include Synthetic A', exact: true }).check()
    await waitAdvice(race, 'Endurance', 'none', ['Synthetic A'])
    return { quiet_window_ms: 650, empty_food_requests: 0, late_response_after_all_excluded_ignored: true }
  })

  await check('new_scan_supersedes_pending_old_scan_advice_and_reset_restores_focus', async () => {
    race.holdNext = 1
    const before = race.held.length
    await race.page.getByLabel('Health context (this session only)').selectOption('diabetic')
    await until(() => race.held.length === before + 1, 'Held old-scan request')
    const old = race.held.at(-1)
    await race.page.getByRole('button', { name: 'Choose another image', exact: true }).click()
    await race.page.getByRole('button', { name: 'Choose Image', exact: true }).waitFor()
    await race.page.waitForTimeout(30)
    assert.equal(await race.page.getByRole('button', { name: 'Choose Image', exact: true }).evaluate(element => element === document.activeElement), true)
    assert.equal(await race.page.locator('.guidance').count(), 0)
    race.foods = fixtures.replacement
    await upload(race)
    const current = await waitAdvice(race, 'Endurance', 'diabetic', ['Synthetic Replacement'])
    await releaseAndCheck(race, old, current)
    assert.equal(await race.page.getByRole('checkbox', { name: 'Include Synthetic A', exact: true }).count(), 0)
    return { network_abort_deliberately_ignored: true, reset_restored_keyboard_focus: true }
  })
  await race.context.close()

  await check('unknown_only_journal_reload_local_date_focus_rollover_mobile_keyboard', async () => {
    const state = await harness({ mobile: true, foods: fixtures.unknown })
    await state.page.clock.install({ time: new Date('2026-09-11T18:31:00Z') })
    await state.page.goto(url)
    const chooser = state.page.getByRole('button', { name: 'Choose Image', exact: true })
    await chooser.focus()
    const picker = state.page.waitForEvent('filechooser')
    await state.page.keyboard.press('Enter')
    await picker
    await upload(state)
    await waitAdvice(state, 'Maintenance', 'none', ['Synthetic Unknown'])
    assert.match(await state.page.getByLabel('Current meal totals', { exact: true }).innerText(), /Totals are unknown/)
    assert.match(await state.page.locator('.daily-number').innerText(), /^0/)
    await state.page.getByRole('button', { name: 'Save meal', exact: true }).click()
    await state.page.getByRole('button', { name: 'Meal saved', exact: true }).waitFor()
    const read = () => state.page.evaluate(key => JSON.parse(localStorage.getItem(key)), storageKey)
    const saved = await read()
    assert.equal(saved.meals.length, 1)
    assert.equal(saved.meals[0].localDate, '2026-09-12')
    assert(saved.meals[0].savedAt.startsWith('2026-09-11'))
    assert.equal(saved.meals[0].items[0].per100g, null)
    const originalId = saved.meals[0].id
    await state.page.reload()
    await state.page.locator('.daily-summary').getByText('Daily totals are incomplete.', { exact: true }).waitFor()
    assert.match(await state.page.locator('.daily-number').innerText(), /^—/)
    assert.equal((await read()).meals[0].id, originalId)
    assert.equal(await state.page.locator('#history article').count(), 1)
    await state.page.getByText('Goals & advanced settings', { exact: true }).click()
    const select = state.page.getByLabel('Health context (this session only)')
    await select.focus()
    await state.page.keyboard.press('Home')
    await state.page.keyboard.press('ArrowDown')
    await state.page.keyboard.press('Enter')
    assert.equal(await select.inputValue(), 'diabetic')
    assert(!/diabetic|imageUrl|data:image|blob:|bounding_box|confidence/.test(JSON.stringify(await read())))
    await state.page.clock.setSystemTime(new Date('2026-09-12T18:31:00Z'))
    await state.page.evaluate(() => window.dispatchEvent(new Event('focus')))
    await state.page.locator('.daily-number').filter({ hasText: /^0/ }).waitFor()
    assert.equal(await state.page.locator('#history article').count(), 1)
    assert.equal((await read()).meals[0].localDate, '2026-09-12')
    assert.equal(await state.page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true)
    assert.equal(await state.page.evaluate(() => matchMedia('(prefers-reduced-motion: reduce)').matches), true)
    const scanBox = await state.page.locator('#scan').boundingBox()
    const summaryBox = await state.page.locator('.daily-summary').boundingBox()
    assert(summaryBox.y > scanBox.y)
    await state.context.close()
    return { viewport: '360x800', timezone: 'Asia/Kolkata', saved_local_date_differs_from_utc: true, unknown_retained_on_reload: true, focus_rollover_preserves_history: true }
  })
  await check('no_page_errors_or_unmocked_external_api_requests', async () => {
    assert.deepEqual(report.page_errors, [])
    assert.deepEqual(report.unexpected_network, [])
    return { page_errors: 0, unexpected_network: 0 }
  })
  report.status = 'pass'
} catch (error) {
  report.status = 'fail'
  report.failure = error.message
  process.exitCode = 1
} finally {
  for (const state of openHarnesses) for (const pending of state.held) pending.release()
  if (browser) await browser.close()
  report.completed_at_utc = new Date().toISOString()
  report.duration_seconds = (performance.now() - started) / 1000
  report.summary = { passed: report.cases.filter(row => row.status === 'pass').length, failed: report.cases.filter(row => row.status === 'fail').length, goal_context_combinations: report.matrix.length }
  const encoded = JSON.stringify(report, null, 2) + '\n'
  for (const target of targets) fs.writeFileSync(target, encoded, { flag: 'wx' })
  console.log(JSON.stringify(ci ? report : { status: report.status, ...report.summary, receipt: path.relative(root, targets[0]), failure: report.failure }))
}
