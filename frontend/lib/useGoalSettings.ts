'use client'

import { useEffect, useState } from 'react'
import { calculateMacros, getConditions, getGoals } from './endpoints'
import { calculateLocalMacros, FALLBACK_HEALTH_CONDITIONS, MacroGoal } from './goals'
import { DEFAULT_PREFERENCES, Journal, Preferences } from './meals'

export function useGoalSettings(saved: Preferences, ready: boolean, commit: (change: (journal: Journal) => Journal) => boolean, onStatus: (status: string) => void) {
  const [preferences, setPreferences] = useState<Preferences>(DEFAULT_PREFERENCES)
  const [goalInput, setGoalInput] = useState(DEFAULT_PREFERENCES.goal)
  const [calorieInput, setCalorieInput] = useState(String(DEFAULT_PREFERENCES.calories))
  const [healthCondition, setHealthCondition] = useState('none')
  const [macroReply, setMacroReply] = useState<{ key: string; value: MacroGoal } | null>(null)
  const [goalError, setGoalError] = useState('')
  const [macroError, setMacroError] = useState('')
  const [conditions, setConditions] = useState(FALLBACK_HEALTH_CONDITIONS)
  const macroKey = `${preferences.goal}:${preferences.calories}:${healthCondition}`
  const macros = macroReply?.key === macroKey ? macroReply.value : calculateLocalMacros(preferences.goal, preferences.calories, healthCondition)
  useEffect(() => {
    if (ready) { setPreferences({ goal: saved.goal, calories: saved.calories }); setGoalInput(saved.goal); setCalorieInput(String(saved.calories)) }
  }, [ready, saved.goal, saved.calories])
  useEffect(() => {
    const controller = new AbortController()
    Promise.all([getGoals(controller.signal), getConditions(controller.signal)]).then(([, data]) => {
      if (!controller.signal.aborted && data.health_conditions.length) setConditions(data.health_conditions)
    }).catch(error => { if (!controller.signal.aborted) setGoalError(`${error.message} Using built-in options.`) })
    return () => controller.abort()
  }, [])
  useEffect(() => {
    const controller = new AbortController()
    setMacroError('')
    const timer = setTimeout(async () => {
      try {
        const value = await calculateMacros({ goal: preferences.goal, target_calories: preferences.calories, health_condition: healthCondition }, controller.signal)
        if (!controller.signal.aborted) setMacroReply({ key: macroKey, value })
      } catch (error) { if (!controller.signal.aborted) setMacroError(`${error instanceof Error ? error.message : 'Goals unavailable.'} Using local macro estimates.`) }
    }, 250)
    return () => { clearTimeout(timer); controller.abort() }
  }, [preferences.goal, preferences.calories, healthCondition, macroKey])
  const applyGoals = () => {
    const calories = Number(calorieInput)
    if (!Number.isInteger(calories) || calories < 500 || calories > 5000) { setGoalError('Enter a daily target between 500 and 5,000 kcal.'); return }
    const next = { goal: goalInput, calories }
    setPreferences(next); setGoalError('')
    onStatus(commit(previous => ({ ...previous, preferences: next })) ? 'Goals saved in this browser.' : 'Goals applied for this session only; they could not be saved.')
  }
  return { preferences, goalInput, setGoalInput, calorieInput, setCalorieInput, healthCondition, setHealthCondition, conditions, macros, goalError, macroError, applyGoals, ready }
}
