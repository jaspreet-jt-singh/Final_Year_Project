'use client'

import { Check, Save } from 'lucide-react'
import RecommendationPanel from './RecommendationPanel'
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
    <RecommendationPanel analysis={analysis} draft={draft} goal={userGoal} health={healthCondition} />
  </section>
}
