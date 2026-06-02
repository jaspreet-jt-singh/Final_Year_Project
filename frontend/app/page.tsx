'use client'

import React, { useState, useCallback, useEffect } from 'react'
import ImageUpload from '@/components/ImageUpload'
import NutritionLabel from '@/components/NutritionLabel'
import ResultsPanel from '@/components/ResultsPanel'
import { Brain, Utensils, Target, Flame, ArrowDown, Camera, RotateCcw, Info, Heart } from 'lucide-react'

interface FoodDetection {
  food_label: string
  display_name: string
  confidence: number
  bounding_box: [number, number, number, number]
  macros: {
    calories: number
    protein_g: number
    carbs_g: number
    fat_g: number
  } | null
  macros_unit: string
  nutrition_source: string | null
  nutrition_not_found?: boolean
}

interface FoodAnalysis {
  detections: FoodDetection[]
  img_width: number | null
  img_height: number | null
  food_not_found: boolean
  message?: string
}

interface MacroGoal {
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

interface GoalOption {
  name: string
  carbs_percent: number
  protein_percent: number
  fat_percent: number
  description: string
}

interface HealthConditionOption {
  name: string
  description: string
}

const FALLBACK_GOALS: GoalOption[] = [
  { name: 'Weight Loss', carbs_percent: 40, protein_percent: 35, fat_percent: 25, description: 'Higher protein, moderate carbs for satiety' },
  { name: 'Muscle Gain', carbs_percent: 40, protein_percent: 30, fat_percent: 30, description: 'Balanced macros for muscle synthesis' },
  { name: 'Maintenance', carbs_percent: 50, protein_percent: 25, fat_percent: 25, description: 'Balanced nutrition for weight maintenance' },
  { name: 'Endurance',   carbs_percent: 55, protein_percent: 20, fat_percent: 20, description: 'Higher carbs for sustained energy' },
]

const FALLBACK_HEALTH_CONDITIONS: HealthConditionOption[] = [
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

function calculateLocalMacros(goal: string, calories: number, healthCondition: string = 'None'): MacroGoal {
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

export default function Home() {
  const [analysis,    setAnalysis]    = useState<FoodAnalysis | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [error,       setError]       = useState<string | null>(null)
  const [imageUrl,    setImageUrl]    = useState<string | null>(null)
  const [noFood,      setNoFood]      = useState(false)

  const [selectedGoal, setSelectedGoal] = useState<string>('Maintenance')
  const [targetCalories, setTargetCalories] = useState<number>(2000)
  const [macroGoal, setMacroGoal] = useState<MacroGoal | null>(null)
  const [consumedCalories, setConsumedCalories] = useState<number>(0)
  const [consumedProtein, setConsumedProtein] = useState<number>(0)
  const [consumedCarbs, setConsumedCarbs] = useState<number>(0)
  const [consumedFat, setConsumedFat] = useState<number>(0)
  const [goalOptions, setGoalOptions] = useState<GoalOption[]>(FALLBACK_GOALS)
  const [showMacroDetails, setShowMacroDetails] = useState(false)
  const [selectedHealthCondition, setSelectedHealthCondition] = useState<string>('None')
  const [healthConditionOptions, setHealthConditionOptions] = useState<HealthConditionOption[]>(FALLBACK_HEALTH_CONDITIONS)
  const [showConditionDetails, setShowConditionDetails] = useState(false)

  const calculateMacros = useCallback(async (goal: string, calories: number, healthCondition: string = 'None') => {
    try {
      const response = await fetch('http://localhost:8000/api/user/calculate-macros', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal, target_calories: calories, health_condition: healthCondition })
      })
      if (response.ok) {
        const data = await response.json()
        setMacroGoal(data)
        return
      }
    } catch {
      // Backend unavailable — use local calculation
    }
    setMacroGoal(calculateLocalMacros(goal, calories, healthCondition))
  }, [])

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        // Fetch goals
        const goalsRes = await fetch('http://localhost:8000/api/user/goals')
        if (goalsRes.ok) {
          const goalsData = await goalsRes.json()
          if (goalsData.goals && goalsData.goals.length > 0) {
            setGoalOptions(goalsData.goals)
          }
        }
        // Fetch health conditions
        const healthRes = await fetch('http://localhost:8000/api/user/health-conditions')
        if (healthRes.ok) {
          const healthData = await healthRes.json()
          if (healthData.health_conditions && healthData.health_conditions.length > 0) {
            setHealthConditionOptions(healthData.health_conditions)
          }
        }
      } catch {
        console.warn('Backend not running — using hardcoded options')
      }
    }
    fetchInitialData()
  }, [])

  useEffect(() => {
    calculateMacros(selectedGoal, targetCalories, selectedHealthCondition)
  }, [selectedGoal, targetCalories, selectedHealthCondition, calculateMacros])

  const remainingCalories = macroGoal ? macroGoal.target_calories - consumedCalories : 0
  const remainingProtein = macroGoal ? macroGoal.protein_g - consumedProtein : 0
  const remainingCarbs = macroGoal ? macroGoal.carbs_g - consumedCarbs : 0
  const remainingFat = macroGoal ? macroGoal.fat_g - consumedFat : 0

  const progressPercent = macroGoal ? Math.min(100, (consumedCalories / macroGoal.target_calories) * 100) : 0

  // Color coding for progress bar
  const getProgressColor = () => {
    if (progressPercent < 50) return 'bg-green-500'
    if (progressPercent < 80) return 'bg-yellow-500'
    if (progressPercent < 100) return 'bg-orange-500'
    return 'bg-red-500'
  }

  const handleGoalChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedGoal(e.target.value)
  }

  const handleCalorieChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const calories = parseInt(e.target.value) || 0
    setTargetCalories(calories)
  }

  const resetAll = useCallback(() => {
    setAnalysis(null)
    setImageUrl(null)
    setError(null)
    setNoFood(false)
    setConsumedCalories(0)
    setConsumedProtein(0)
    setConsumedCarbs(0)
    setConsumedFat(0)
  }, [])

  const analyzeFood = useCallback(async (file: File) => {
    setIsAnalyzing(true)
    setError(null)
    setAnalysis(null)
    setNoFood(false)

    const reader = new FileReader()
    reader.onload = (e) => setImageUrl(e.target?.result as string)
    reader.readAsDataURL(file)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const controller = new AbortController()
      const timeout = setTimeout(() => controller.abort(), 30000)

      const response = await fetch('http://localhost:8000/api/analyze-food', {
        method: 'POST',
        body  : formData,
        signal: controller.signal,
      })
      clearTimeout(timeout)

      let result: FoodAnalysis
      try {
        result = await response.json()
      } catch {
        throw new Error(`Server returned non-JSON response (status ${response.status})`)
      }

      if (!response.ok && response.status >= 500) {
        throw new Error((result as any).detail || `Server error ${response.status}`)
      }

      if (!result.detections || result.detections.length === 0) {
        setNoFood(true)
        return
      }

      let totalCalories = 0
      let totalProtein = 0
      let totalCarbs = 0
      let totalFat = 0

      result.detections.forEach(det => {
        if (det.macros) {
          totalCalories += det.macros.calories || 0
          totalProtein += det.macros.protein_g || 0
          totalCarbs += det.macros.carbs_g || 0
          totalFat += det.macros.fat_g || 0
        }
      })

      setConsumedCalories(totalCalories)
      setConsumedProtein(totalProtein)
      setConsumedCarbs(totalCarbs)
      setConsumedFat(totalFat)
      setAnalysis(result)

    } catch (err: any) {
      console.error('Error analyzing food:', err)
      let errorMessage = ''
      if (err?.name === 'AbortError') {
        errorMessage = 'Request timed out — make sure the backend is running:\n\ncd backend\npython main.py'
      } else if (err instanceof TypeError && err.message.includes('fetch')) {
        errorMessage = 'Cannot connect to backend — please start the server:\n\ncd backend\npython main.py'
      } else if (err instanceof Error) {
        errorMessage = err.message
      } else {
        errorMessage = 'Failed to analyze food — please try again'
      }
      setError(errorMessage)
    } finally {
      setIsAnalyzing(false)
    }
  }, [])

  return (
    <main className="min-h-screen bg-gradient-to-br from-orange-50 via-white to-amber-50">
      {/* Top Status Bar */}
      {macroGoal && (
        <div className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-200 shadow-sm">
          <div className="container mx-auto px-4 py-2">
            <div className="flex items-center justify-between max-w-2xl mx-auto">
              <div className="flex items-center space-x-3">
                <Flame className="w-5 h-5 text-orange-500" />
                <span className="text-sm font-medium text-gray-700">
                  {Math.max(0, remainingCalories)} <span className="text-gray-500">kcal remaining</span>
                </span>
              </div>
              <div className="flex items-center space-x-4">
                {analysis && (
                  <button
                    onClick={resetAll}
                    className="text-xs text-gray-500 hover:text-gray-700 flex items-center space-x-1 transition-colors"
                  >
                    <RotateCcw className="w-3 h-3" />
                    <span>Reset</span>
                  </button>
                )}
                <div className="flex items-center space-x-2">
                  <span className="text-xs text-gray-500">{selectedGoal}</span>
                  <span className="text-xs text-gray-400">|</span>
                  <span className="text-xs text-gray-500">{targetCalories} kcal</span>
                </div>
              </div>
            </div>
            {/* Mini progress bar */}
            <div className="max-w-2xl mx-auto mt-1">
              <div className="w-full bg-gray-100 rounded-full h-1.5">
                <div
                  className={`h-1.5 rounded-full transition-all duration-700 ${getProgressColor()}`}
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="container mx-auto px-4 py-8">

        {/* Header */}
        <div className="text-center mb-10 animate-fade-in">
          <div className="flex justify-center items-center space-x-3 mb-6">
            <div className="p-3 bg-gradient-to-br from-orange-500 to-amber-600 rounded-2xl shadow-lg shadow-orange-200">
              <Brain className="w-8 h-8 text-white" />
            </div>
            <div className="p-3 bg-gradient-to-br from-green-500 to-emerald-600 rounded-2xl shadow-lg shadow-green-200">
              <Utensils className="w-8 h-8 text-white" />
            </div>
          </div>
          <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-2">
            AI Food Recognition
          </h1>
          <p className="text-lg text-gray-600">
            Upload a photo and get instant nutrition analysis with smart recommendations
          </p>
        </div>

        {/* Phase 2: Goal Selection & Target Calories */}
        <div className="max-w-2xl mx-auto mb-6 animate-slide-up">
          <div className="bg-white rounded-2xl shadow-md border border-gray-100 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900 flex items-center">
                <Target className="w-5 h-5 mr-2 text-orange-500" />
                Set Your Daily Goal
              </h2>
              <button
                onClick={() => setShowMacroDetails(!showMacroDetails)}
                className="text-xs text-gray-500 hover:text-gray-700 flex items-center space-x-1"
              >
                <Info className="w-3 h-3" />
                <span>{showMacroDetails ? 'Hide details' : 'Show details'}</span>
              </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Dietary Goal
                </label>
                <select
                  value={selectedGoal}
                  onChange={handleGoalChange}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-transparent bg-white text-gray-900"
                >
                  {goalOptions.map((option) => (
                    <option key={option.name} value={option.name}>
                      {option.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Daily Calories
                </label>
                <input
                  type="number"
                  value={targetCalories}
                  onChange={handleCalorieChange}
                  min="500"
                  max="5000"
                  step="50"
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-transparent text-gray-900"
                />
              </div>
            </div>
            
            {/* Macro breakdown (collapsible) */}
            {macroGoal && showMacroDetails && (
              <div className="mt-4 pt-4 border-t border-gray-100 animate-fade-in">
                <div className="grid grid-cols-3 gap-3">
                  <div className="text-center p-3 bg-blue-50 rounded-xl">
                    <div className="text-xs text-blue-600 font-medium">Carbs</div>
                    <div className="text-lg font-bold text-gray-900">{macroGoal.carbs_g}g</div>
                    <div className="text-xs text-gray-500">{macroGoal.carbs_percent}%</div>
                  </div>
                  <div className="text-center p-3 bg-green-50 rounded-xl">
                    <div className="text-xs text-green-600 font-medium">Protein</div>
                    <div className="text-lg font-bold text-gray-900">{macroGoal.protein_g}g</div>
                    <div className="text-xs text-gray-500">{macroGoal.protein_percent}%</div>
                  </div>
                  <div className="text-center p-3 bg-purple-50 rounded-xl">
                    <div className="text-xs text-purple-600 font-medium">Fat</div>
                    <div className="text-lg font-bold text-gray-900">{macroGoal.fat_g}g</div>
                    <div className="text-xs text-gray-500">{macroGoal.fat_percent}%</div>
                  </div>
                </div>
                <p className="mt-2 text-xs text-gray-500 text-center">{macroGoal.description}</p>
              </div>
            )}

            {/* Health Condition Selector */}
            <div className="mt-4 pt-4 border-t border-gray-100">
              <div className="flex items-center justify-between mb-3">
                <label className="text-sm font-medium text-gray-700 flex items-center">
                  <Heart className="w-4 h-4 mr-1.5 text-red-500" />
                  Health Condition
                </label>
                <button
                  onClick={() => setShowConditionDetails(!showConditionDetails)}
                  className="text-xs text-gray-500 hover:text-gray-700 flex items-center space-x-1"
                >
                  <Info className="w-3 h-3" />
                  <span>{showConditionDetails ? 'Hide' : 'What is this?'}</span>
                </button>
              </div>
              <select
                value={selectedHealthCondition}
                onChange={(e) => setSelectedHealthCondition(e.target.value)}
                className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-red-500 focus:border-transparent bg-white text-gray-900 mb-2"
              >
                {healthConditionOptions.map((option) => (
                  <option key={option.name} value={option.name}>
                    {option.name}
                  </option>
                ))}
              </select>
              {showConditionDetails && selectedHealthCondition !== 'None' && (
                <p className="text-xs text-gray-500 mt-1 animate-fade-in">
                  {healthConditionOptions.find(c => c.name === selectedHealthCondition)?.description || ''}
                </p>
              )}
              {selectedHealthCondition !== 'None' && (
                <div className="mt-2 flex items-center space-x-2 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                  <Heart className="w-3.5 h-3.5 text-red-500 flex-shrink-0" />
                  <p className="text-xs text-red-700">
                    Macros and recommendations will be adapted for <strong>{selectedHealthCondition}</strong>
                  </p>
                </div>
              )}
            </div>

            {/* Quick calorie presets */}
            <div className="mt-4">
              <label className="block text-xs text-gray-500 mb-2">Quick select:</label>
              <div className="flex flex-wrap gap-2">
                {[1500, 1800, 2000, 2200, 2500].map(cal => (
                  <button
                    key={cal}
                    onClick={() => setTargetCalories(cal)}
                    className={`px-3 py-1.5 text-xs rounded-full border transition-all ${
                      targetCalories === cal
                        ? 'bg-orange-500 text-white border-orange-500'
                        : 'bg-gray-50 text-gray-600 border-gray-200 hover:border-orange-300'
                    }`}
                  >
                    {cal}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Phase 2: Remaining Calories Card (compact, shown only after detection) */}
        {macroGoal && (consumedCalories > 0 || analysis) && (
          <div className="max-w-2xl mx-auto mb-6 animate-slide-up">
            <div className="bg-gradient-to-r from-green-50 to-emerald-50 rounded-2xl border border-green-200 p-5">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <div className="p-2.5 bg-green-100 rounded-xl">
                    <Flame className="w-6 h-6 text-green-600" />
                  </div>
                  <div>
                    <p className="text-xs text-gray-600 font-medium">REMAINING TODAY</p>
                    <p className="text-3xl font-bold text-gray-900">
                      {Math.max(0, remainingCalories)}
                      <span className="text-base font-normal text-gray-500 ml-1">kcal</span>
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-xs text-gray-600 font-medium">CONSUMED</p>
                  <p className="text-xl font-bold text-gray-800">{consumedCalories}</p>
                  <p className="text-xs text-gray-500">of {macroGoal.target_calories}</p>
                </div>
              </div>
              {/* Progress bar with color coding */}
              <div className="mt-3">
                <div className="w-full bg-gray-200 rounded-full h-2.5">
                  <div
                    className={`h-2.5 rounded-full transition-all duration-700 ${getProgressColor()}`}
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
              </div>

              {/* Quick macros consumed vs remaining */}
              <div className="mt-3 grid grid-cols-3 gap-2">
                <div className="text-center p-2 bg-white/60 rounded-lg">
                  <div className="text-[10px] text-gray-500 font-medium">CARBS</div>
                  <div className="text-sm font-bold text-gray-700">
                    {consumedCarbs}g <span className="text-gray-400 text-xs">/ {macroGoal.carbs_g}g</span>
                  </div>
                </div>
                <div className="text-center p-2 bg-white/60 rounded-lg">
                  <div className="text-[10px] text-gray-500 font-medium">PROTEIN</div>
                  <div className="text-sm font-bold text-gray-700">
                    {consumedProtein}g <span className="text-gray-400 text-xs">/ {macroGoal.protein_g}g</span>
                  </div>
                </div>
                <div className="text-center p-2 bg-white/60 rounded-lg">
                  <div className="text-[10px] text-gray-500 font-medium">FAT</div>
                  <div className="text-sm font-bold text-gray-700">
                    {consumedFat}g <span className="text-gray-400 text-xs">/ {macroGoal.fat_g}g</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="max-w-2xl mx-auto mb-6 animate-slide-up">
            <div className="bg-red-50 border border-red-200 rounded-2xl p-5">
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0 w-8 h-8 bg-red-100 rounded-full flex items-center justify-center">
                  <svg className="h-4 w-4 text-red-500" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-semibold text-red-800">Something went wrong</h3>
                  <p className="mt-1 text-sm text-red-700 whitespace-pre-line">{error}</p>
                </div>
                <button
                  onClick={() => setError(null)}
                  className="flex-shrink-0 text-red-400 hover:text-red-600"
                >
                  <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* No Food Detected */}
        {noFood && (
          <div className="max-w-2xl mx-auto mb-6 animate-slide-up">
            <div className="bg-yellow-50 border border-yellow-200 rounded-2xl p-5 text-center">
              <Camera className="w-8 h-8 text-yellow-500 mx-auto mb-2" />
              <p className="text-yellow-800 font-medium">No food detected in this image.</p>
              <p className="text-yellow-600 text-sm mt-1">Try a clearer photo with good lighting and the food centered.</p>
            </div>
          </div>
        )}

        {/* Upload & Results */}
        <div className="space-y-8">
          {/* Upload Section */}
          <div className="text-center">
            <h2 className="text-2xl font-semibold text-gray-900 mb-6 flex items-center justify-center">
              <Camera className="w-6 h-6 mr-2 text-orange-500" />
              Upload Food Image
            </h2>
            <ImageUpload onImageSelect={analyzeFood} isAnalyzing={isAnalyzing} />
          </div>

          {/* Downward arrow indicator */}
          {(analysis || isAnalyzing) && (
            <div className="flex justify-center animate-bounce">
              <ArrowDown className="w-6 h-6 text-orange-400" />
            </div>
          )}

          {/* Results Section */}
          {(analysis || isAnalyzing) && (
            <div className="animate-fade-in">
              <h2 className="text-2xl font-semibold text-gray-900 mb-6 text-center flex items-center justify-center">
                <Utensils className="w-6 h-6 mr-2 text-green-500" />
                Analysis Results
              </h2>
              <ResultsPanel 
                analysis={analysis} 
                imageUrl={imageUrl} 
                isLoading={isAnalyzing} 
                userGoal={selectedGoal}
                healthCondition={selectedHealthCondition}
              />
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="mt-16 text-center">
          <p className="text-sm text-gray-400">
            AI Food Recognition · Final Year Project · Jaspreet Singh
          </p>
        </div>

      </div>
    </main>
  )
}