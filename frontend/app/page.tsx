'use client'

import React, { useState, useCallback, useEffect } from 'react'
import ImageUpload from '@/components/ImageUpload'
import NutritionLabel from '@/components/NutritionLabel'
import ResultsPanel from '@/components/ResultsPanel'
import { Brain, Utensils, Target, Flame } from 'lucide-react'

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

// Hardcoded fallback goals — always work even without backend
const FALLBACK_GOALS: GoalOption[] = [
  { name: 'Weight Loss', carbs_percent: 40, protein_percent: 35, fat_percent: 25, description: 'Higher protein, moderate carbs, lower fat for satiety and muscle preservation' },
  { name: 'Muscle Gain', carbs_percent: 40, protein_percent: 30, fat_percent: 30, description: 'Balanced macros with adequate protein for muscle synthesis' },
  { name: 'Maintenance', carbs_percent: 50, protein_percent: 25, fat_percent: 25, description: 'Balanced nutrition for maintaining current weight' },
  { name: 'Endurance',   carbs_percent: 55, protein_percent: 20, fat_percent: 20, description: 'Higher carbs for sustained energy during endurance activities' }
]

// Local macro calculation — always works even without backend
function calculateLocalMacros(goal: string, calories: number): MacroGoal {
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
  
  return {
    goal, goal_key: goalKey, target_calories: calories,
    carbs_g: Math.round((calories * split.carbs_pct / 100) / 4),
    protein_g: Math.round((calories * split.protein_pct / 100) / 4),
    fat_g: Math.round((calories * split.fat_pct / 100) / 9),
    carbs_percent: split.carbs_pct, protein_percent: split.protein_pct, fat_percent: split.fat_pct,
    description: descMap[goal] || ''
  }
}

export default function Home() {
  const [analysis,    setAnalysis]    = useState<FoodAnalysis | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [error,       setError]       = useState<string | null>(null)
  const [imageUrl,    setImageUrl]    = useState<string | null>(null)
  const [noFood,      setNoFood]      = useState(false)

  // Phase 2: User goals and macro tracking
  const [selectedGoal, setSelectedGoal] = useState<string>('Maintenance')
  const [targetCalories, setTargetCalories] = useState<number>(2000)
  const [macroGoal, setMacroGoal] = useState<MacroGoal | null>(null)
  const [consumedCalories, setConsumedCalories] = useState<number>(0)
  const [consumedProtein, setConsumedProtein] = useState<number>(0)
  const [consumedCarbs, setConsumedCarbs] = useState<number>(0)
  const [consumedFat, setConsumedFat] = useState<number>(0)
  // Start with hardcoded fallback so dropdown always works
  const [goalOptions, setGoalOptions] = useState<GoalOption[]>(FALLBACK_GOALS)

  // Calculate macros (tries backend first, falls back to local calculation)
  const calculateMacros = useCallback(async (goal: string, calories: number) => {
    try {
      const response = await fetch('http://localhost:8000/api/user/calculate-macros', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal, target_calories: calories })
      })
      if (response.ok) {
        const data = await response.json()
        setMacroGoal(data)
        return
      }
    } catch {
      // Backend unavailable — use local calculation
    }
    // Fallback: calculate locally
    setMacroGoal(calculateLocalMacros(goal, calories))
  }, [])

  // Try to fetch goals from backend (overrides fallback if available)
  useEffect(() => {
    const fetchGoals = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/user/goals')
        if (response.ok) {
          const data = await response.json()
          if (data.goals && data.goals.length > 0) {
            setGoalOptions(data.goals)
          }
        }
      } catch {
        console.warn('Backend not running — using hardcoded goal options')
      }
    }
    fetchGoals()
  }, [])

  // Update macros when goal or calories change
  useEffect(() => {
    calculateMacros(selectedGoal, targetCalories)
  }, [selectedGoal, targetCalories, calculateMacros])

  // Calculate remaining values
  const remainingCalories = macroGoal ? macroGoal.target_calories - consumedCalories : 0
  const remainingProtein = macroGoal ? macroGoal.protein_g - consumedProtein : 0
  const remainingCarbs = macroGoal ? macroGoal.carbs_g - consumedCarbs : 0
  const remainingFat = macroGoal ? macroGoal.fat_g - consumedFat : 0

  // Handle goal change
  const handleGoalChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const goal = e.target.value
    setSelectedGoal(goal)
  }

  // Handle calorie change
  const handleCalorieChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const calories = parseInt(e.target.value) || 0
    setTargetCalories(calories)
  }

  // Reset consumed when new analysis starts
  const resetConsumed = useCallback(() => {
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
    resetConsumed()

    // Preview — for display only, does NOT affect what's sent to API
    const reader = new FileReader()
    reader.onload = (e) => setImageUrl(e.target?.result as string)
    reader.readAsDataURL(file)

    try {
      // ✅ FormData key is 'file' — matches FastAPI param name exactly
      const formData = new FormData()
      formData.append('file', file)

      // ✅ No Content-Type header — browser sets multipart boundary automatically
      const controller = new AbortController()
      const timeout = setTimeout(() => controller.abort(), 30000) // 30s timeout

      const response = await fetch('http://localhost:8000/api/analyze-food', {
        method: 'POST',
        body  : formData,
        signal: controller.signal,
      })
      clearTimeout(timeout)

      // FIX: parse JSON first regardless of status
      let result: FoodAnalysis
      try {
        result = await response.json()
      } catch {
        throw new Error(`Server returned non-JSON response (status ${response.status})`)
      }

      // FIX: only throw on actual server errors (5xx), not 404/no-detection
      if (!response.ok && response.status >= 500) {
        throw new Error((result as any).detail || `Server error ${response.status}`)
      }

      // FIX: Handle empty detections array (no food found)
      if (!result.detections || result.detections.length === 0) {
        setNoFood(true)
        return
      }

      // Calculate total consumed from detections
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
        errorMessage = 'Request timed out — please make sure the backend is running at http://localhost:8000'
      } else if (err instanceof TypeError && err.message.includes('fetch')) {
        errorMessage = 'Cannot connect to backend — please start the server first:\n\ncd backend\npython main.py'
      } else if (err instanceof Error) {
        errorMessage = err.message
      } else {
        errorMessage = 'Failed to analyze food — please try again'
      }
      setError(errorMessage)
    } finally {
      setIsAnalyzing(false)
    }
  }, [resetConsumed])

  return (
    <main className="min-h-screen bg-gradient-to-br from-primary-50 to-white">
      <div className="container mx-auto px-4 py-8">

        {/* Header */}
        <div className="text-center mb-12">
          <div className="flex justify-center items-center space-x-3 mb-4">
            <div className="p-3 bg-primary-600 rounded-full">
              <Brain className="w-8 h-8 text-white" />
            </div>
            <div className="p-3 bg-orange-600 rounded-full">
              <Utensils className="w-8 h-8 text-white" />
            </div>
          </div>
          <h1 className="text-4xl font-bold text-gray-900 mb-2">AI Based Food Recognition</h1>
          <p className="text-xl text-gray-600 mb-2">with Nutrition Aware Recommendations</p>
        </div>

        {/* Phase 2: Goal Selection & Target Calories */}
        <div className="max-w-2xl mx-auto mb-8">
          <div className="card">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
              <Target className="w-5 h-5 mr-2 text-primary-600" />
              Set Your Daily Goal
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Dietary Goal
                </label>
                <select
                  value={selectedGoal}
                  onChange={handleGoalChange}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                >
                  {goalOptions.map((option) => (
                    <option key={option.name} value={option.name}>
                      {option.name}
                    </option>
                  ))}
                </select>
                {macroGoal && (
                  <p className="mt-2 text-sm text-gray-600">
                    {macroGoal.description}
                  </p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Target Calories (kcal)
                </label>
                <input
                  type="number"
                  value={targetCalories}
                  onChange={handleCalorieChange}
                  min="500"
                  max="5000"
                  step="50"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
                {macroGoal && (
                  <div className="mt-3 space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Carbs:</span>
                      <span className="font-medium">{macroGoal.carbs_g}g ({macroGoal.carbs_percent}%)</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Protein:</span>
                      <span className="font-medium">{macroGoal.protein_g}g ({macroGoal.protein_percent}%)</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Fat:</span>
                      <span className="font-medium">{macroGoal.fat_g}g ({macroGoal.fat_percent}%)</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Phase 2: Remaining Calories Card */}
        {macroGoal && (consumedCalories > 0 || analysis) && (
          <div className="max-w-2xl mx-auto mb-8">
            <div className="card bg-gradient-to-r from-green-50 to-emerald-50 border-green-200">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-green-100 rounded-full">
                    <Flame className="w-6 h-6 text-green-600" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Remaining Today</p>
                    <p className="text-3xl font-bold text-gray-900">
                      {Math.max(0, remainingCalories)} <span className="text-lg font-normal text-gray-600">kcal</span>
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm text-gray-600">Consumed</p>
                  <p className="text-xl font-semibold text-gray-900">{consumedCalories} kcal</p>
                </div>
              </div>
              {/* Progress bar */}
              <div className="mt-4">
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-green-500 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${Math.min(100, (consumedCalories / macroGoal.target_calories) * 100)}%` }}
                  />
                </div>
                <div className="flex justify-between mt-1 text-xs text-gray-500">
                  <span>0 kcal</span>
                  <span>{macroGoal.target_calories} kcal</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="max-w-2xl mx-auto mb-8">
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-red-800">Error</h3>
                  <p className="mt-2 text-sm text-red-700 whitespace-pre-line">{error}</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* No Food Detected — soft message, not an error */}
        {noFood && (
          <div className="max-w-2xl mx-auto mb-8">
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-center">
              <p className="text-yellow-800 font-medium">No food detected in this image.</p>
              <p className="text-yellow-600 text-sm mt-1">Try a clearer photo with good lighting.</p>
            </div>
          </div>
        )}

        <div className="space-y-8">
          {/* Upload Section */}
          <div className="text-center">
            <h2 className="text-2xl font-semibold text-gray-900 mb-6">Upload Food Image</h2>
            <ImageUpload onImageSelect={analyzeFood} isAnalyzing={isAnalyzing} />
          </div>

          {/* Results Section */}
          {(analysis || isAnalyzing) && (
            <div className="text-center">
              <h2 className="text-2xl font-semibold text-gray-900 mb-6">Analysis Results</h2>
              <ResultsPanel 
                analysis={analysis} 
                imageUrl={imageUrl} 
                isLoading={isAnalyzing} 
                userGoal={selectedGoal}
              />
            </div>
          )}
        </div>


      </div>
    </main>
  )
}