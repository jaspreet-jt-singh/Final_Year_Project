'use client'

import { useEffect, useState } from 'react'
import { recommendations } from './endpoints'
import { ApiError } from './api'
import { conditionOption, resolveCondition } from './goals'
import type { FoodAnalysis, MealDraft } from './meals'

type State =
  | { status: 'idle'; key: string }
  | { status: 'loading'; key: string }
  | { status: 'error'; key: string; error: ApiError }
  | { status: 'success'; key: string; recommendations: string[]; source: string; condition: string }

export function useRecommendations(analysis: FoodAnalysis, draft: MealDraft, goal: string, health: string) {
  const condition = resolveCondition(health)
  const included = draft.items.map(item => item.included ? '1' : '0').join('')
  const key = JSON.stringify([draft.id, included, goal, condition])
  const hasFoods = included.includes('1')
  const [stored, setStored] = useState<State>({ status: 'idle', key: '' })
  const [retryNumber, setRetryNumber] = useState(0)
  // Derived state hides previous advice on the very render the context changes.
  const state: State = stored.key === key ? stored : { status: hasFoods ? 'loading' : 'idle', key }

  useEffect(() => {
    const controller = new AbortController()
    if (!hasFoods) { setStored({ status: 'idle', key }); return }
    setStored({ status: 'loading', key })
    const timer = setTimeout(async () => {
      try {
        const result = await recommendations({ detected_foods: analysis.detections.filter((_, index) => included[index] === '1').slice(0, 10), user_goal: goal, health_condition: condition }, controller.signal)
        if (!controller.signal.aborted) setStored({ status: 'success', key, recommendations: result.recommendations, source: result.source, condition: result.health_condition })
      } catch (error) {
        if (!controller.signal.aborted) setStored({ status: 'error', key, error: error instanceof ApiError ? error : new ApiError('Guidance could not be loaded.', 'invalid-response') })
      }
    }, 400)
    return () => { clearTimeout(timer); controller.abort() }
  }, [analysis, key, included, hasFoods, goal, condition, retryNumber])

  return { state, option: conditionOption(condition), retry: () => { setStored({ status: 'loading', key }); setRetryNumber(number => number + 1) } }
}
