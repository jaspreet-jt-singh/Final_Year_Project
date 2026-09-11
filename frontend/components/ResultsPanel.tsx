'use client'

import { useEffect, useState } from 'react'
import { Check, Save, Sparkles } from 'lucide-react'
import { apiFetch } from '@/lib/api'
import { FoodAnalysis, MealDraft, totalNutrition } from '@/lib/meals'
import MealItems, { NutritionTotals } from './MealItems'

interface ResultsPanelProps {
  analysis: FoodAnalysis
  imageUrl: string
  draft: MealDraft
  onChange: (draft: MealDraft) => void
  onSave: () => void
  saved: boolean
  dirty: boolean
  canSave: boolean
  userGoal: string
  healthCondition: string
}

export default function ResultsPanel({ analysis, imageUrl, draft, onChange, onSave, saved, dirty, canSave, userGoal, healthCondition }: ResultsPanelProps) {
  const [recommendations, setRecommendations] = useState<string[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [source, setSource] = useState('')
  const [retry, setRetry] = useState(0)
  // Portion edits do not trigger extra AI calls. Excluded foods cannot influence advice.
  const included = draft.items.map(item => item.included ? '1' : '0').join('')
  useEffect(() => {
    const controller = new AbortController()
    const foods = analysis.detections.filter((_, i) => included[i] === '1').slice(0, 10)
    setRecommendations([]); setError(''); setSource('')
    if (!foods.length) { setLoading(false); return }
    setLoading(true)
    const timer = setTimeout(async () => {
      try {
        const response = await apiFetch('/api/recommendations', { method: 'POST', signal: controller.signal,
          headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ detected_foods: foods, user_goal: userGoal, health_condition: healthCondition }) })
        const data = await response.json()
        if (controller.signal.aborted) return
        if (!Array.isArray(data.recommendations) || !data.recommendations.length) throw new Error('No guidance is available right now.')
        setRecommendations(data.recommendations); setSource(data.source || 'fallback')
      } catch (err) { if (!controller.signal.aborted) setError(err instanceof Error ? err.message : 'Guidance could not be loaded.') }
      finally { if (!controller.signal.aborted) setLoading(false) }
    }, 400)
    return () => { clearTimeout(timer); controller.abort() }
  }, [analysis, included, userGoal, healthCondition, retry])

  const totals = totalNutrition(draft.items)
  return <section className="space-y-6" aria-labelledby="review-heading">
    <div className="section-heading"><div><p className="eyebrow">02 / Review portions</p><h2 id="review-heading">Your meal, a little clearer.</h2></div><span className="pill">{analysis.detections.length} detected</span></div>
    <p className="muted">Portions are your estimates—not weights measured from the photo. Adjust the grams and exclude any incorrect detections.</p>
    {analysis.img_width && analysis.img_height && <details className="panel compact">
      <summary>View detection image & confidence</summary>
      <div className="relative mt-4 overflow-hidden rounded-2xl">
        <img src={imageUrl} alt="Detected foods" className="block w-full h-auto" />
        {analysis.detections.map((food, i) => <div key={i} className="absolute border-2 border-orange-600 pointer-events-none" style={{
          left: `${food.bounding_box[0] / analysis.img_width! * 100}%`, top: `${food.bounding_box[1] / analysis.img_height! * 100}%`,
          width: `${(food.bounding_box[2] - food.bounding_box[0]) / analysis.img_width! * 100}%`, height: `${(food.bounding_box[3] - food.bounding_box[1]) / analysis.img_height! * 100}%`,
        }}><span className="absolute top-0 left-0 bg-orange-800 text-white text-xs px-1">{i + 1}</span></div>)}
      </div>
      <ul className="mt-4 space-y-2 text-sm">{analysis.detections.map((food, i) => <li key={i}>{i + 1}. {food.display_name} — {(food.confidence * 100).toFixed(0)}% detection confidence</li>)}</ul>
      <p className="muted text-xs mt-3">Confidence describes the model prediction, not nutrition accuracy.</p>
    </details>}
    <MealItems items={draft.items} onChange={items => onChange({ ...draft, items })} prefix="scan" />
    <div className="panel meal-total">
      <p className="eyebrow mb-3">This meal · estimated totals</p>
      <NutritionTotals totals={totals} label="Current meal totals" />
      <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
        <p className="muted text-sm">{saved ? dirty ? 'Save your changes to update daily totals.' : 'Included in your saved daily totals.' : 'Only saved meals count toward your day.'}</p>
        <button className="btn-primary" disabled={!canSave || !totals.itemCount || (saved && !dirty)} onClick={onSave}>{saved && !dirty ? <Check size={18} /> : <Save size={18} />}{saved ? dirty ? 'Update saved meal' : 'Meal saved' : 'Save meal'}</button>
      </div>
    </div>
    <section className="panel guidance" aria-labelledby="guidance-heading">
      <div className="flex items-center gap-2 mb-3"><Sparkles size={20} /><h3 id="guidance-heading" className="font-semibold text-lg">A little food guidance</h3></div>
      {loading && <p role="status" className="muted">Preparing suggestions for your food choices…</p>}
      {error && <div><p role="alert" className="notice">{error} Your food analysis is still available.</p><button className="btn-secondary mt-3" onClick={() => setRetry(value => value + 1)}>Retry guidance</button></div>}
      {!totals.itemCount && <p className="muted">Include a food to see suggestions.</p>}
      {recommendations.length > 0 && <><ul className="space-y-3 list-disc pl-5">{recommendations.map((advice, i) => <li key={i} className="text-sm leading-relaxed">{advice}</li>)}</ul><p className="muted text-xs mt-4">{source === 'groq' ? 'AI-generated suggestions' : 'Local fallback suggestions'} · {userGoal}</p></>}
      <p className="muted text-xs mt-4">General food-choice guidance, not portion-specific or medical advice. Consult a qualified professional for medical dietary needs.</p>
    </section>
  </section>
}
