'use client'

import { useState } from 'react'
import { MealDraft, SavedMeal, sameItems, saveDraft, totalNutrition } from './meals'
import { useJournal } from './useJournal'

export function useMealJournal(draft: MealDraft | null, setDraft: (draft: MealDraft | null) => void, setStatus: (status: string) => void) {
  const { journal, commit, ready, today, storageError } = useJournal()
  const [deleted, setDeleted] = useState<SavedMeal | null>(null)
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

  return { journal, commit, ready, today, storageError, deleted, setDeleted, todaysMeals, daily, saved, dirty, saveMeal, editMeal, deleteMeal, undoDelete }
}
