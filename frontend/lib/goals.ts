export interface MacroGoal {
  goal: string
  goal_key: string
  target_calories: number
  carbs_g: number
  protein_g: number
  fat_g: number
  carbs_percent: number
  protein_percent: number
  fat_percent: number
  description: string
}

export interface GoalOption {
  name: string
  carbs_percent: number
  protein_percent: number
  fat_percent: number
  description: string
}

export interface HealthConditionOption {
  name: string
  description: string
}

export const FALLBACK_GOALS: GoalOption[] = [
  { name: 'Weight Loss', carbs_percent: 40, protein_percent: 35, fat_percent: 25, description: 'Higher protein, moderate carbs for satiety' },
  { name: 'Muscle Gain', carbs_percent: 40, protein_percent: 30, fat_percent: 30, description: 'Balanced macros for muscle synthesis' },
  { name: 'Maintenance', carbs_percent: 50, protein_percent: 25, fat_percent: 25, description: 'Balanced nutrition for weight maintenance' },
  { name: 'Endurance',   carbs_percent: 55, protein_percent: 20, fat_percent: 20, description: 'Higher carbs for sustained energy' },
]

export const FALLBACK_HEALTH_CONDITIONS: HealthConditionOption[] = [
  { name: 'None', description: 'No specific health conditions' },
  { name: 'Diabetic', description: 'Focus on low glycemic index foods, manage blood sugar spikes' },
  { name: 'Hypertension (High BP)', description: 'Low sodium diet, avoid processed foods' },
  { name: 'Heart Disease', description: 'Low saturated fat, low cholesterol' },
  { name: 'High Cholesterol', description: 'Low saturated/trans fats, high fiber' },
  { name: 'Digestive Issues', description: 'Easily digestible foods, small frequent meals' },
  { name: 'Kidney Disease', description: 'Low potassium, controlled protein intake' },
  { name: 'Anemia', description: 'Iron-rich foods, vitamin C to aid absorption' },
  { name: 'Thyroid Disorder', description: 'Iodine balance, selenium-rich foods' },
]

export function calculateLocalMacros(goal: string, calories: number, healthCondition: string = 'None'): MacroGoal {
  // Health condition macro modifiers (mirrors backend logic for offline mode)
  const conditionModifiers: Record<string, { carbs: number; protein: number; fat: number }> = {
    'None':                    { carbs: 1.0, protein: 1.0, fat: 1.0 },
    'Diabetic':                { carbs: 0.8, protein: 1.15, fat: 1.0 },
    'Hypertension (High BP)':  { carbs: 1.0, protein: 1.0, fat: 0.9 },
    'Heart Disease':           { carbs: 1.05, protein: 1.0, fat: 0.8 },
    'High Cholesterol':        { carbs: 1.05, protein: 1.1, fat: 0.75 },
    'Digestive Issues':        { carbs: 1.0, protein: 0.9, fat: 0.85 },
    'Kidney Disease':          { carbs: 1.15, protein: 0.6, fat: 1.0 },
    'Anemia':                  { carbs: 1.0, protein: 1.1, fat: 0.9 },
    'Thyroid Disorder':        { carbs: 1.0, protein: 1.05, fat: 1.0 },
  }

  const goalMap: Record<string, { carbs_pct: number; protein_pct: number; fat_pct: number }> = {
    'Weight Loss': { carbs_pct: 40, protein_pct: 35, fat_pct: 25 },
    'Muscle Gain': { carbs_pct: 40, protein_pct: 30, fat_pct: 30 },
    'Maintenance': { carbs_pct: 50, protein_pct: 25, fat_pct: 25 },
    'Endurance':   { carbs_pct: 55, protein_pct: 20, fat_pct: 20 },
  }
  const split = goalMap[goal] || goalMap['Maintenance']
  const goalKey = goal.toLowerCase().replace(/\s+/g, '_')
  const descMap: Record<string, string> = {}
  FALLBACK_GOALS.forEach(g => { descMap[g.name] = g.description })
  
  // Apply condition modifiers
  const mods = conditionModifiers[healthCondition] || conditionModifiers['None']
  const totalMod = (split.carbs_pct * mods.carbs) + (split.protein_pct * mods.protein) + (split.fat_pct * mods.fat)
  const carbsPct = Math.round((split.carbs_pct * mods.carbs) / totalMod * 100)
  const proteinPct = Math.round((split.protein_pct * mods.protein) / totalMod * 100)
  const fatPct = 100 - carbsPct - proteinPct
  
  let description = descMap[goal] || ''
  if (healthCondition !== 'None') {
    const condDesc = FALLBACK_HEALTH_CONDITIONS.find(c => c.name === healthCondition)
    if (condDesc) description += ` | Adapted for ${healthCondition}`
  }
  
  return {
    goal, goal_key: goalKey, target_calories: calories,
    carbs_g: Math.round((calories * carbsPct / 100) / 4),
    protein_g: Math.round((calories * proteinPct / 100) / 4),
    fat_g: Math.round((calories * fatPct / 100) / 9),
    carbs_percent: carbsPct, protein_percent: proteinPct, fat_percent: fatPct,
    description
  }
}


