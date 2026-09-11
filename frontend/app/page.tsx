'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { ArrowRight, Flame, Leaf, Utensils } from 'lucide-react'
import ImageUpload from '@/components/ImageUpload'
import ResultsPanel from '@/components/ResultsPanel'
import MealHistory from '@/components/MealHistory'
import { NutritionTotals } from '@/components/MealItems'
import { apiFetch } from '@/lib/api'
import { createDraft, DEFAULT_PREFERENCES, FoodAnalysis, GOALS, MealDraft, Preferences, SavedMeal, saveDraft, sameItems, totalNutrition } from '@/lib/meals'
import { calculateLocalMacros, FALLBACK_HEALTH_CONDITIONS, MacroGoal } from '@/lib/goals'
import { useJournal } from '@/lib/useJournal'

export default function Home() {
  const { journal, commit, ready, today, storageError } = useJournal()
  const [analysis, setAnalysis] = useState<FoodAnalysis | null>(null)
  const [draft, setDraft] = useState<MealDraft | null>(null)
  const [imageUrl, setImageUrl] = useState<string | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const running = useRef(false)
  const request = useRef<AbortController | null>(null)
  const [error, setError] = useState('')
  const [status, setStatus] = useState('')
  const [deleted, setDeleted] = useState<SavedMeal | null>(null)
  const [preferences, setPreferences] = useState<Preferences>(DEFAULT_PREFERENCES)
  const [goalInput, setGoalInput] = useState(DEFAULT_PREFERENCES.goal)
  const [calorieInput, setCalorieInput] = useState(String(DEFAULT_PREFERENCES.calories))
  const [healthCondition, setHealthCondition] = useState('None')
  const [macroReply, setMacroReply] = useState<{ key: string; value: MacroGoal } | null>(null)
  const [goalError, setGoalError] = useState('')
  const [macroError, setMacroError] = useState('')
  const [conditions, setConditions] = useState(FALLBACK_HEALTH_CONDITIONS)
  const macroKey = `${preferences.goal}:${preferences.calories}:${healthCondition}`
  const macros = macroReply?.key === macroKey ? macroReply.value : calculateLocalMacros(preferences.goal, preferences.calories, healthCondition)

  useEffect(() => {
    if (ready) { setPreferences({ goal: journal.preferences.goal, calories: journal.preferences.calories }); setGoalInput(journal.preferences.goal); setCalorieInput(String(journal.preferences.calories)) }
  }, [ready, journal.preferences.goal, journal.preferences.calories])
  useEffect(() => () => { if (imageUrl) URL.revokeObjectURL(imageUrl) }, [imageUrl])
  useEffect(() => () => request.current?.abort(), [])

  useEffect(() => {
    const controller = new AbortController()
    const fetchOptions = async () => {
      try {
        // Preserve both existing option endpoints without blocking photo upload.
        const [goalsResponse, conditionsResponse] = await Promise.all([
          apiFetch('/api/user/goals', { signal: controller.signal }), apiFetch('/api/user/health-conditions', { signal: controller.signal }),
        ])
        await goalsResponse.json()
        const data = await conditionsResponse.json()
        if (!controller.signal.aborted && Array.isArray(data.health_conditions) && data.health_conditions.length) setConditions(data.health_conditions)
      } catch (err) {
        if (!controller.signal.aborted) setGoalError(`${err instanceof Error ? err.message : 'Goal options unavailable.'} Using built-in options.`)
      }
    }
    void fetchOptions()
    return () => controller.abort()
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    setMacroError('')
    const timer = setTimeout(async () => {
      try {
        const response = await apiFetch('/api/user/calculate-macros', { method: 'POST', signal: controller.signal, headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ goal: preferences.goal, target_calories: preferences.calories, health_condition: healthCondition }) })
        const value = await response.json()
        if (!controller.signal.aborted) setMacroReply({ key: macroKey, value })
      } catch (err) { if (!controller.signal.aborted) setMacroError(`${err instanceof Error ? err.message : 'Goals unavailable.'} Using local macro estimates.`) }
    }, 250)
    return () => { clearTimeout(timer); controller.abort() }
  }, [preferences.goal, preferences.calories, healthCondition, macroKey])

  const analyzeFood = useCallback(async (processed: File) => {
    if (running.current) return
    running.current = true
    request.current?.abort()
    const controller = new AbortController()
    request.current = controller
    setBusy(true); setError(''); setStatus(''); setAnalysis(null); setDraft(null)
    setFile(processed); setImageUrl(URL.createObjectURL(processed))
    try {
      const data = new FormData(); data.append('file', processed)
      const response = await apiFetch('/api/analyze-food', { method: 'POST', body: data, signal: controller.signal }, 120000)
      const result: FoodAnalysis = await response.json()
      if (controller.signal.aborted) return
      if (!Array.isArray(result.detections)) throw new Error('The analyzer returned an invalid response. Please try again.')
      setAnalysis(result)
      if (result.detections.length) {
        setDraft(createDraft(result, crypto.randomUUID()))
        setStatus(`Detected ${result.detections.length} Food Item${result.detections.length === 1 ? '' : 's'}. Review portions before saving.`)
      } else setStatus('No food detected in this image.')
    } catch (err) {
      if (!controller.signal.aborted) setError(err instanceof Error && err.name !== 'AbortError' ? err.message : 'Analysis took too long. Please wait a moment and try again.')
    } finally {
      running.current = false
      if (!controller.signal.aborted) setBusy(false)
    }
  }, [])

  const reset = () => { setAnalysis(null); setDraft(null); setImageUrl(null); setFile(null); setError(''); setStatus('') }
  const todaysMeals = journal.meals.filter(meal => meal.localDate === today)
  const daily = totalNutrition(todaysMeals.flatMap(meal => meal.items))
  const saved = draft ? journal.meals.find(meal => meal.id === draft.id) : undefined
  const dirty = !!draft && !sameItems(saved?.items, draft.items)
  const saveMeal = () => {
    if (draft && commit(previous => ({ ...previous, meals: saveDraft(previous.meals, draft) }))) setStatus(saved ? 'Saved meal updated.' : 'Meal saved to your journal.')
  }
  const editMeal = (meal: SavedMeal) => {
    if (!commit(previous => ({ ...previous, meals: saveDraft(previous.meals, meal) }))) return false
    if (draft?.id === meal.id) setDraft({ id: meal.id, items: meal.items })
    setStatus('Saved meal updated.'); return true
  }
  const deleteMeal = (meal: SavedMeal) => {
    if (commit(previous => ({ ...previous, meals: previous.meals.filter(item => item.id !== meal.id) }))) { setDeleted(meal); setStatus('Meal deleted. You can undo this below.') }
  }
  const undoDelete = () => {
    if (deleted && commit(previous => ({ ...previous, meals: [...previous.meals.filter(meal => meal.id !== deleted.id), deleted] }))) { setDeleted(null); setStatus('Meal restored.') }
  }

  return <main id="main" className="site-shell">
    <a className="skip-link" href="#scan">Skip to food upload</a>
    <header className="site-header"><a href="#main" className="brand"><span className="brand-icon"><Utensils size={22} /></span><span>AI Food Recognition<span className="brand-subtitle">Nutrition-aware recommendations</span></span></a><a href="#history" className="text-button">Meal journal <ArrowRight size={15} /></a></header>
    <section className="hero"><p className="eyebrow flex items-center gap-2"><Leaf size={16} /> A little awareness. A better everyday.</p><h1>Know your plate.<br /><span>Nourish your day.</span></h1><p>Turn a food photo into a clearer picture of your meal.<br className="hidden sm:block" /> Review your portions, save your meals, and find your balance.</p>
      <ol className="steps" aria-label="Meal workflow"><li><span>1</span>Scan</li><li><span>2</span>Review portions</li><li><span>3</span>Save meal</li></ol>
    </section>
    {storageError && <p role="alert" className="notice mb-6">{storageError}</p>}
    <div className="dashboard-grid">
      <div className="min-w-0 space-y-7">
        <section id="scan" className="panel" aria-labelledby="scan-heading"><div className="section-heading"><div><p className="eyebrow">01 / Start with a photo</p><h2 id="scan-heading">Let’s see your meal.</h2></div><span className="pill">Food scanner</span></div>
          <ImageUpload onImageSelect={analyzeFood} isAnalyzing={busy} previewUrl={imageUrl} onReset={reset} />
          {error && <div className="notice mt-4"><p role="alert">{error}</p>{file && <button className="btn-secondary mt-3" disabled={busy} onClick={() => void analyzeFood(file)}>Retry analysis</button>}</div>}
          {analysis && !analysis.detections.length && <p className="notice mt-4">Try a clearer photo with good lighting and the food centered.</p>}
          <p role="status" aria-live="polite" className={status ? 'scan-status' : 'sr-only'}>{status}</p>
          <p className="muted text-xs mt-4">Your photo is processed for analysis, never saved in your meal journal.</p>
        </section>
      </div>
      <aside className="dashboard-aside min-w-0 space-y-5" aria-label="Daily summary and settings">
        <section className="panel daily-summary" aria-labelledby="daily-heading"><div className="flex items-center justify-between mb-5"><p id="daily-heading" className="eyebrow">Today’s saved meals</p><Flame size={22} /></div>
          <p className="daily-number">{daily.incomplete && !daily.knownItems ? '—' : Math.round(daily.calories)}<span>kcal{daily.incomplete ? ' known' : ''}</span></p>
          <p className="muted text-sm mt-1">of your {preferences.calories.toLocaleString()} kcal target · {todaysMeals.length} saved meal{todaysMeals.length === 1 ? '' : 's'}</p>
          <div className="daily-track" role="progressbar" aria-label="Known calories against daily target" aria-valuemin={0} aria-valuemax={preferences.calories} aria-valuenow={Math.min(preferences.calories, Math.round(daily.calories))} aria-valuetext={`${Math.round(daily.calories)} known calories; target ${preferences.calories}${daily.incomplete ? '; totals incomplete' : ''}`}><span style={{ width: `${Math.min(100, daily.calories / preferences.calories * 100)}%` }} /></div>
          <p className="text-sm font-medium mb-5">{daily.incomplete ? `Daily totals are incomplete.${daily.calories > preferences.calories ? ` Known foods are already ${Math.round(daily.calories - preferences.calories)} kcal above your target.` : ''}` : daily.calories > preferences.calories ? `${Math.round(daily.calories - preferences.calories)} kcal above your target` : `${Math.round(preferences.calories - daily.calories)} kcal remaining`}</p>
          <NutritionTotals totals={daily} label="Today nutrition totals" />
          <p className="muted text-xs mt-4">Your current scan is counted only after you save it.</p>
        </section>
        <details className="panel compact"><summary>Goals & advanced settings</summary><p className="muted text-sm mt-3">Set your own daily target. These are general estimates, not prescribed dietary goals.</p>
          <form className="space-y-4 mt-5" onSubmit={event => {
            event.preventDefault()
            const calories = Number(calorieInput)
            if (!Number.isInteger(calories) || calories < 500 || calories > 5000) { setGoalError('Enter a daily target between 500 and 5,000 kcal.'); return }
            const next = { goal: goalInput, calories }
            setPreferences(next); setGoalError('')
            if (commit(previous => ({ ...previous, preferences: next }))) setStatus('Goals saved in this browser.')
            else setStatus('Goals applied for this session only; they could not be saved.')
          }}>
            <label className="field">Your goal<select value={goalInput} onChange={e => setGoalInput(e.target.value)}>{GOALS.map(goal => <option key={goal}>{goal}</option>)}</select></label>
            <label className="field">Daily calorie target<input type="number" min="500" max="5000" step="1" required value={calorieInput} onChange={e => setCalorieInput(e.target.value)} /></label>
            <button className="btn-secondary" disabled={!ready}>Save goals</button>
          </form>
          {goalError && <p role="alert" className="notice mt-3">{goalError}</p>}
          <label className="field mt-5">Health context (this session only)<select value={healthCondition} onChange={e => setHealthCondition(e.target.value)}>{conditions.map(condition => <option key={condition.name}>{condition.name}</option>)}</select></label>
          <p className="muted text-xs mt-2">This selection is sent to the recommendation service but is not saved in your browser history.</p>
          {macroError && <p role="alert" className="notice mt-3">{macroError}</p>}
          <p className="eyebrow mt-5 mb-2">Estimated daily macro targets</p><p className="text-sm">Protein {macros.protein_g} g · Carbs {macros.carbs_g} g · Fat {macros.fat_g} g</p>
        </details>
        <div className="privacy-note"><Leaf size={18} className="shrink-0" /><p>A private little journal.<br /><span>Meals stay on this device. Photos don’t.</span></p></div>
      </aside>
      {analysis && draft && imageUrl && <div className="review-section min-w-0"><ResultsPanel analysis={analysis} draft={draft} imageUrl={imageUrl} onChange={setDraft} onSave={saveMeal} saved={!!saved} dirty={dirty} canSave={ready} userGoal={preferences.goal} healthCondition={healthCondition} /></div>}
    </div>
    <div className="mt-9">
      {deleted && <div className="notice mb-4 flex flex-wrap items-center justify-between gap-3"><span>Meal removed from your journal.</span><button className="btn-secondary" onClick={undoDelete}>Undo delete</button></div>}
      <MealHistory meals={journal.meals} today={today} onEdit={editMeal} onDelete={deleteMeal} onClear={() => {
        if (!commit(previous => ({ ...previous, meals: [] }))) return false
        setDeleted(null); setStatus('Meal history cleared. Goals were kept.'); return true
      }} />
    </div>
    <footer className="site-footer"><span>AI Food Recognition · Final Year Project</span><span>Nutrition estimates, not medical advice.</span></footer>
  </main>
}
