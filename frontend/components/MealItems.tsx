'use client'

import { Minus, Plus } from 'lucide-react'
import { MealItem, totalNutrition, Totals } from '@/lib/meals'

export function NutritionTotals({ totals, label }: { totals: Totals; label: string }) {
  const unknown = totals.incomplete && totals.knownItems === 0
  return <div aria-label={label}>
    <div className="macro-grid">
      {([['calories', 'Calories', 'kcal'], ['protein_g', 'Protein', 'g'], ['carbs_g', 'Carbs', 'g'], ['fat_g', 'Fat', 'g']] as const).map(([key, name, unit]) =>
        <div key={key}><span className="eyebrow">{name}</span><p className="macro-value">{unknown ? '—' : Math.round(totals[key])}<span>{unknown ? '' : unit}</span></p></div>)}
    </div>
    {totals.incomplete && <p className="notice mt-3">Incomplete estimate: nutrition is unavailable for {totals.itemCount - totals.knownItems} included food{totals.itemCount - totals.knownItems === 1 ? '' : 's'}. {unknown ? 'Totals are unknown.' : 'Only foods with known nutrition are counted.'}</p>}
  </div>
}

export default function MealItems({ items, onChange, prefix }: { items: MealItem[]; onChange: (items: MealItem[]) => void; prefix: string }) {
  const update = (id: string, changes: Partial<MealItem>) => onChange(items.map(item => item.id === id ? { ...item, ...changes } : item))
  return <div className="space-y-4">{items.map((item, index) => <div key={item.id} className={`food-card ${!item.included ? 'food-excluded' : ''}`}>
    <div className="flex items-start justify-between gap-3">
      <div className="min-w-0"><span className="eyebrow">Food {index + 1}</span><h3 className="text-lg font-semibold break-words">{item.name}</h3></div>
      <label className="inline-flex items-center gap-2 text-sm shrink-0"><input type="checkbox" checked={item.included} onChange={e => update(item.id, { included: e.target.checked })} aria-label={`Include ${item.name}`} />Include</label>
    </div>
    <div className="portion-row">
      <label htmlFor={`${prefix}-${item.id}`} className="text-sm font-medium">Portion (g)</label>
      <div className="flex items-center gap-2">
        <button type="button" className="icon-button" aria-label={`Decrease ${item.name} portion`} disabled={!item.included || item.grams <= 25} onClick={() => update(item.id, { grams: item.grams - 25 })}><Minus size={16} /></button>
        <select id={`${prefix}-${item.id}`} value={item.grams} disabled={!item.included} onChange={e => update(item.id, { grams: Number(e.target.value) })} className="portion-select">{Array.from({ length: 40 }, (_, i) => (i + 1) * 25).map(grams => <option key={grams} value={grams}>{grams} g</option>)}</select>
        <button type="button" className="icon-button" aria-label={`Increase ${item.name} portion`} disabled={!item.included || item.grams >= 1000} onClick={() => update(item.id, { grams: item.grams + 25 })}><Plus size={16} /></button>
      </div>
    </div>
    {item.included ? <NutritionTotals totals={totalNutrition([item])} label={`${item.name} estimated nutrition`} /> : <p className="muted text-sm">Excluded from this meal and its totals.</p>}
    <p className="muted text-xs mt-3">Nutrition source: {item.source || 'Unavailable'} · Values scaled from 100 g.</p>
  </div>)}</div>
}
