'use client'

import { useState } from 'react'
import { MealItem, SavedMeal, totalNutrition } from '@/lib/meals'
import MealItems, { NutritionTotals } from './MealItems'

export default function MealHistory({ meals, today, onEdit, onDelete, onClear }: {
  meals: SavedMeal[]; today: string; onEdit: (meal: SavedMeal) => boolean; onDelete: (meal: SavedMeal) => void; onClear: () => boolean
}) {
  const [editing, setEditing] = useState<string | null>(null)
  const [items, setItems] = useState<MealItem[]>([])
  const [confirmClear, setConfirmClear] = useState(false)
  const dates = Array.from(new Set(meals.map(meal => meal.localDate))).sort().reverse()
  return <section id="history" className="panel" aria-labelledby="history-heading">
    <div className="section-heading"><div><p className="eyebrow">03 / Your journal</p><h2 id="history-heading">Meals worth remembering.</h2></div>
      {meals.length > 0 && <button className="text-button" onClick={() => setConfirmClear(true)}>Clear history</button>}</div>
    <p className="muted text-sm mb-6">Saved only in this browser, without photos. Clearing browser data removes your history. No account or cross-device sync.</p>
    {confirmClear && <div className="notice mb-5" role="group" aria-label="Confirm clear history"><p>Delete all saved meals from this browser? This cannot be undone. Your goals will be kept.</p><div className="flex flex-wrap gap-3 mt-3"><button className="btn-secondary" onClick={() => setConfirmClear(false)}>Keep history</button><button className="btn-danger" onClick={() => { if (onClear()) { setConfirmClear(false); setEditing(null) } }}>Delete all meals</button></div></div>}
    {!meals.length && <div className="empty-journal"><p className="font-medium">Your next meal is a fresh start.</p><p className="muted text-sm mt-2">Scan a photo, review the portions, then save it here.</p></div>}
    {dates.map(date => <div key={date} className="mb-6 last:mb-0"><h3 className="eyebrow mb-3">{date === today ? 'Today' : new Date(`${date}T12:00:00`).toLocaleDateString(undefined, { day: 'numeric', month: 'long', year: 'numeric' })}</h3>
      {meals.filter(meal => meal.localDate === date).sort((a, b) => b.savedAt.localeCompare(a.savedAt)).map(meal => <article key={meal.id} className="history-meal" aria-label={`Saved meal ${meal.items.filter(item => item.included).map(item => item.name).join(', ')}`}>
        <div className="flex justify-between gap-3 mb-3"><h4 className="font-semibold break-words">{meal.items.filter(item => item.included).map(item => item.name).join(' + ')}</h4><time className="muted text-xs shrink-0" dateTime={meal.savedAt}>{new Date(meal.savedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</time></div>
        {editing === meal.id ? <><MealItems items={items} onChange={setItems} prefix="history" /><div className="flex gap-3 mt-3"><button className="btn-primary" disabled={!items.some(item => item.included)} onClick={() => { if (onEdit({ ...meal, items })) setEditing(null) }}>Save changes</button><button className="btn-secondary" onClick={() => setEditing(null)}>Cancel</button></div></> : <>
          <p className="muted text-sm mb-3">{meal.items.filter(item => item.included).map(item => `${item.grams} g ${item.name}`).join(' · ')}</p>
          <NutritionTotals totals={totalNutrition(meal.items)} label="Saved meal totals" />
          <div className="flex gap-4 mt-3"><button className="text-button" onClick={() => { setEditing(meal.id); setItems(meal.items) }}>Edit portions</button><button className="text-button" onClick={() => onDelete(meal)}>Delete meal</button></div>
        </>}
      </article>)}
    </div>)}
  </section>
}
