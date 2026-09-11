import { Flame } from 'lucide-react'
import { Totals } from '@/lib/meals'
import { NutritionTotals } from './MealItems'

export default function DailySummary({ totals, targetCalories, mealCount }: { totals: Totals; targetCalories: number; mealCount: number }) {
  return (<section className="panel daily-summary" aria-labelledby="daily-heading"><div className="flex items-center justify-between mb-5"><p id="daily-heading" className="eyebrow">Today’s saved meals</p><Flame size={22} /></div>
          <p className="daily-number">{totals.incomplete && !totals.knownItems ? '—' : Math.round(totals.calories)}<span>kcal{totals.incomplete ? ' known' : ''}</span></p>
          <p className="muted text-sm mt-1">of your {targetCalories.toLocaleString()} kcal target · {mealCount} saved meal{mealCount === 1 ? '' : 's'}</p>
          <div className="daily-track" role="progressbar" aria-label="Known calories against daily target" aria-valuemin={0} aria-valuemax={targetCalories} aria-valuenow={Math.min(targetCalories, Math.round(totals.calories))} aria-valuetext={`${Math.round(totals.calories)} known calories; target ${targetCalories}${totals.incomplete ? '; totals incomplete' : ''}`}><span style={{ width: `${Math.min(100, totals.calories / targetCalories * 100)}%` }} /></div>
          <p className="text-sm font-medium mb-5">{totals.incomplete ? `Daily totals are incomplete.${totals.calories > targetCalories ? ` Known foods are already ${Math.round(totals.calories - targetCalories)} kcal above your target.` : ''}` : totals.calories > targetCalories ? `${Math.round(totals.calories - targetCalories)} kcal above your target` : `${Math.round(targetCalories - totals.calories)} kcal remaining`}</p>
          <NutritionTotals totals={totals} label="Today nutrition totals" />
          <p className="muted text-xs mt-4">Your current scan is counted only after you save it.</p>
        </section>)
}
