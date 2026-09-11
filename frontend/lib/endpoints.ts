import { ApiError, apiFetch } from './api'
import type { components } from './generated/api'
import { conditionOption, resolveCondition } from './goals'

type Schemas = components['schemas']
const object = (value: unknown): value is Record<string, unknown> => !!value && typeof value === 'object' && !Array.isArray(value)
const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value) && value >= 0
const strings = (value: unknown): value is string[] => Array.isArray(value) && value.every(item => typeof item === 'string' && item.trim().length > 0)
const macros = (value: unknown) => object(value) && ['calories', 'protein_g', 'carbs_g', 'fat_g'].every(key => finite(value[key]))
const optionalText = (value: unknown) => value === undefined || value === null || typeof value === 'string'

async function json<T>(path: string, options: RequestInit, validate: (data: unknown) => boolean, timeout?: number): Promise<T> {
  const response = await apiFetch(path, options, timeout)
  try {
    const data: unknown = await response.json()
    if (!validate(data)) throw new Error('Contract mismatch')
    return data as T
  } catch {
    throw new ApiError('The server returned an invalid response. Please retry.', 'invalid-response', response.status, undefined, response.headers.get('X-Request-ID') ?? undefined)
  }
}
const post = (body: unknown, signal?: AbortSignal): RequestInit => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal })

export function analyzeFood(file: File, signal?: AbortSignal) {
  const body = new FormData(); body.append('file', file)
  return json<Schemas['FoodAnalysis']>('/api/analyze-food', { method: 'POST', body, signal }, value => object(value) && typeof value.food_not_found === 'boolean' &&
    Array.isArray(value.detections) && (value.detections.length === 0 || (finite(value.img_width) && value.img_width > 0 && finite(value.img_height) && value.img_height > 0)) &&
    value.detections.every(food => object(food) && typeof food.food_label === 'string' && typeof food.display_name === 'string' && finite(food.confidence) && food.confidence <= 1 &&
      Array.isArray(food.bounding_box) && food.bounding_box.length === 4 && food.bounding_box.every(finite) && (food.macros === null || macros(food.macros)) && food.macros_unit === 'per_100g' && (food.nutrition_source === null || typeof food.nutrition_source === 'string') && optionalText(food.nutrition_source_url) && optionalText(food.nutrition_mapping_note)), 120000)
}

export function recommendations(body: Schemas['RecommendationRequest'], signal?: AbortSignal) {
  const expected = resolveCondition(body.health_condition || 'none')
  return json<Schemas['RecommendationResponse']>('/api/recommendations', post(body, signal), value => object(value) && strings(value.recommendations) && value.recommendations.length === 3 &&
    ['groq', 'fallback', 'openai', 'ollama'].includes(value.source as string) && value.health_condition === expected)
}

export function calculateMacros(body: Schemas['MacroCalculationRequest'], signal?: AbortSignal) {
  return json<Schemas['MacroGoal']>('/api/user/calculate-macros', post(body, signal), value => object(value) &&
    ['target_calories', 'carbs_g', 'protein_g', 'fat_g', 'carbs_percent', 'protein_percent', 'fat_percent'].every(key => finite(value[key])) &&
    value.target_calories === body.target_calories && value.health_condition_key === resolveCondition(body.health_condition || 'none') && typeof value.goal === 'string' && typeof value.goal_key === 'string' && typeof value.description === 'string' && typeof value.health_condition === 'string')
}

export function getGoals(signal?: AbortSignal) {
  return json<Schemas['GoalsResponse']>('/api/user/goals', { signal }, value => object(value) && Array.isArray(value.goals) && value.goals.every(goal => object(goal) && typeof goal.name === 'string' && typeof goal.description === 'string' && ['carbs_percent', 'protein_percent', 'fat_percent'].every(key => finite(goal[key]))))
}

export function getConditions(signal?: AbortSignal) {
  return json<Schemas['ConditionsResponse']>('/api/user/health-conditions', { signal }, value => object(value) && Array.isArray(value.health_conditions) && value.health_conditions.every(condition => {
    if (!object(condition) || typeof condition.key !== 'string' || typeof condition.name !== 'string' || typeof condition.description !== 'string') return false
    try { return conditionOption(condition.key).adjustment_label === condition.adjustment_label } catch { return false }
  }))
}
