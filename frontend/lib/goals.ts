import { nutritionPolicy } from './generated/nutritionPolicy'
import type { components } from './generated/api'

export type MacroGoal = components['schemas']['MacroGoal']
export type GoalOption = components['schemas']['GoalOption']
export type HealthConditionOption = components['schemas']['ConditionOption']
export type HealthConditionKey = keyof typeof nutritionPolicy.conditions
export const FALLBACK_GOALS: GoalOption[] = Object.values(nutritionPolicy.goals)
export const FALLBACK_HEALTH_CONDITIONS: HealthConditionOption[] = Object.values(nutritionPolicy.conditions)
const normalized = (value: string) => value.trim().toLowerCase().replace(/[\s_()-]+/g, ' ').trim()

export function resolveCondition(value: string): HealthConditionKey {
  const option = Object.values(nutritionPolicy.conditions).find(condition => condition.aliases.some(alias => normalized(alias) === normalized(value)))
  if (!option) throw new Error('Unsupported health condition')
  return option.key
}

export function conditionOption(value: string): HealthConditionOption {
  return nutritionPolicy.conditions[resolveCondition(value)]
}

// Match Python's ties-to-even rounding to keep offline targets identical.
function roundEven(value: number): number {
  const base = Math.floor(value)
  return value - base === 0.5 ? base + base % 2 : Math.round(value)
}

export function calculateLocalMacros(goal: string, calories: number, healthCondition = 'none'): MacroGoal {
  const key = (Object.keys(nutritionPolicy.goals) as Array<keyof typeof nutritionPolicy.goals>).find(key => normalized(key) === normalized(goal) || normalized(nutritionPolicy.goals[key].name) === normalized(goal))
  if (!key) throw new Error('Unsupported goal')
  const split = nutritionPolicy.goals[key]
  const condition = resolveCondition(healthCondition)
  const option = nutritionPolicy.conditions[condition]
  const mods = nutritionPolicy.modifiers[condition]
  const total = split.carbs_percent * mods.carbs + split.protein_percent * mods.protein + split.fat_percent * mods.fat
  const carbs = roundEven(split.carbs_percent * mods.carbs / total * 100)
  const protein = roundEven(split.protein_percent * mods.protein / total * 100)
  const fat = 100 - carbs - protein
  return {
    goal: split.name, goal_key: key, target_calories: calories,
    carbs_g: roundEven(calories * carbs / 100 / 4), protein_g: roundEven(calories * protein / 100 / 4), fat_g: roundEven(calories * fat / 100 / 9),
    carbs_percent: carbs, protein_percent: protein, fat_percent: fat,
    description: split.description + (condition === 'none' ? '' : ` | Adapted for ${option.name}: ${option.description}`),
    health_condition: option.name, health_condition_key: condition,
  }
}
