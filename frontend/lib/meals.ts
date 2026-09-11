import type { components } from './generated/api'
import { nutritionPolicy } from './generated/nutritionPolicy'

export type Macros = components['schemas']['Macros']
export type FoodDetection = components['schemas']['FoodDetection']
export type FoodAnalysis = components['schemas']['FoodAnalysis']

export interface MealItem {
  id: string
  foodLabel: string
  name: string
  grams: number
  included: boolean
  per100g: Macros | null
  source: string | null
}

export interface MealDraft { id: string; items: MealItem[] }
export interface SavedMeal extends MealDraft { savedAt: string; localDate: string }
export interface Totals extends Macros { incomplete: boolean; knownItems: number; itemCount: number }
export interface Preferences { goal: string; calories: number }
export interface Journal { version: 1; meals: SavedMeal[]; preferences: Preferences }

export function sameItems(left: MealItem[] | undefined, right: MealItem[]): boolean {
  const signature = (items: MealItem[]) => JSON.stringify(items.map(item => [item.id, item.foodLabel, item.name, item.grams, item.included, item.source,
    item.per100g ? [item.per100g.calories, item.per100g.protein_g, item.per100g.carbs_g, item.per100g.fat_g] : null]))
  return !!left && signature(left) === signature(right)
}

export const STORAGE_KEY = 'food-recognition.journal'
export const GOALS: string[] = Object.values(nutritionPolicy.goals).map(goal => goal.name)
export const DEFAULT_PREFERENCES: Preferences = { goal: 'Maintenance', calories: 2000 }
export const emptyJournal = (): Journal => ({ version: 1, meals: [], preferences: { ...DEFAULT_PREFERENCES } })

export function localDate(date = new Date()): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

export function millisecondsToMidnight(now = new Date()): number {
  const next = new Date(now)
  next.setHours(24, 0, 0, 0)
  return Math.max(1, next.getTime() - now.getTime())
}

export function totalNutrition(items: MealItem[]): Totals {
  const total: Totals = { calories: 0, protein_g: 0, carbs_g: 0, fat_g: 0, incomplete: false, knownItems: 0, itemCount: 0 }
  for (const item of items.filter(item => item.included)) {
    total.itemCount++
    if (!item.per100g) { total.incomplete = true; continue }
    total.knownItems++
    for (const key of ['calories', 'protein_g', 'carbs_g', 'fat_g'] as const) total[key] += item.per100g[key] * item.grams / 100
  }
  return total
}

export function createDraft(analysis: FoodAnalysis, id: string): MealDraft {
  return { id, items: analysis.detections.map((food, index) => ({
    id: `${id}-${index}`, foodLabel: food.food_label, name: food.display_name || food.food_label.replace(/_/g, ' '),
    grams: 100, included: true, per100g: food.nutrition_not_found ? null : food.macros, source: food.nutrition_source,
  })) }
}

// Upsert by draft identity: double clicks cannot create duplicate meals.
export function saveDraft(meals: SavedMeal[], draft: MealDraft, now = new Date()): SavedMeal[] {
  if (!draft.items.some(item => item.included)) throw new Error('Include at least one food before saving.')
  const existing = meals.find(meal => meal.id === draft.id)
  const saved: SavedMeal = { ...draft, savedAt: existing?.savedAt ?? now.toISOString(), localDate: existing?.localDate ?? localDate(now) }
  return [saved, ...meals.filter(meal => meal.id !== draft.id)].sort((a, b) => b.savedAt.localeCompare(a.savedAt))
}

const record = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null && !Array.isArray(value)
const shortString = (value: unknown): value is string => typeof value === 'string' && value.length > 0 && value.length <= 500
const validMacros = (value: unknown): value is Macros => record(value) &&
  ['calories', 'protein_g', 'carbs_g', 'fat_g'].every(key => typeof value[key] === 'number' && Number.isFinite(value[key]) && value[key] >= 0 && value[key] <= 100000)
const validItem = (item: unknown): item is MealItem => record(item) && shortString(item.id) && shortString(item.name) && shortString(item.foodLabel) &&
  typeof item.grams === 'number' && item.grams >= 25 && item.grams <= 1000 && item.grams % 25 === 0 && typeof item.included === 'boolean' &&
  (item.per100g === null || validMacros(item.per100g)) && (item.source === null || shortString(item.source))

export function parseJournal(raw: string | null): Journal {
  if (raw === null) return emptyJournal()
  const value: unknown = JSON.parse(raw)
  if (!record(value)) throw new Error('The saved journal is damaged.')
  if (value.version !== 1) throw new Error('This journal uses an unsupported version. Its data has not been changed.')
  const prefs = value.preferences
  if (!record(prefs) || !GOALS.includes(prefs.goal as string) || typeof prefs.calories !== 'number' || !Number.isInteger(prefs.calories) || prefs.calories < 500 || prefs.calories > 5000 || !Array.isArray(value.meals)) throw new Error('The saved journal is damaged.')
  const seen = new Set<string>()
  for (const meal of value.meals) {
    if (!record(meal) || !shortString(meal.id) || seen.has(meal.id) || typeof meal.savedAt !== 'string' || !Number.isFinite(Date.parse(meal.savedAt)) ||
      typeof meal.localDate !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(meal.localDate) || !Number.isFinite(Date.parse(`${meal.localDate}T12:00:00Z`)) || new Date(`${meal.localDate}T12:00:00Z`).toISOString().slice(0, 10) !== meal.localDate ||
      !Array.isArray(meal.items) || meal.items.length === 0 || !meal.items.every(validItem) || !meal.items.some(item => item.included) || new Set(meal.items.map(item => item.id)).size !== meal.items.length) throw new Error('The saved journal is damaged.')
    seen.add(meal.id)
  }
  // Reconstruct only the public storage shape; unknown properties are not retained.
  return { version: 1, preferences: { goal: prefs.goal as string, calories: prefs.calories }, meals: (value.meals as SavedMeal[]).map(meal => ({
    id: meal.id, savedAt: meal.savedAt, localDate: meal.localDate, items: meal.items.map(item => ({
      id: item.id, name: item.name, foodLabel: item.foodLabel, grams: item.grams, included: item.included, source: item.source,
      per100g: item.per100g ? { calories: item.per100g.calories, protein_g: item.per100g.protein_g, carbs_g: item.per100g.carbs_g, fat_g: item.per100g.fat_g } : null,
    })),
  })) }
}
