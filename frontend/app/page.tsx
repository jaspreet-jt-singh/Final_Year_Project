'use client'

import React, { useState, useCallback } from 'react'
import ImageUpload from '@/components/ImageUpload'
import NutritionLabel from '@/components/NutritionLabel'
import ResultsPanel from '@/components/ResultsPanel'
import { Brain, Utensils } from 'lucide-react'

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

export default function Home() {
  const [analysis,    setAnalysis]    = useState<FoodAnalysis | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [error,       setError]       = useState<string | null>(null)
  const [imageUrl,    setImageUrl]    = useState<string | null>(null)
  // FIX: track "no detection" separately from error — it's not an error
  const [noFood,      setNoFood]      = useState(false)

  const analyzeFood = useCallback(async (file: File) => {
    setIsAnalyzing(true)
    setError(null)
    setAnalysis(null)
    setNoFood(false)

    // Preview — for display only, does NOT affect what's sent to API
    const reader = new FileReader()
    reader.onload = (e) => setImageUrl(e.target?.result as string)
    reader.readAsDataURL(file)

    try {
      // ✅ FormData key is 'file' — matches FastAPI param name exactly
      const formData = new FormData()
      formData.append('file', file)

      // ✅ No Content-Type header — browser sets multipart boundary automatically
      const response = await fetch('http://localhost:8000/api/analyze-food', {
        method: 'POST',
        body  : formData,
      })

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

      setAnalysis(result)

    } catch (err) {
      console.error('Error analyzing food:', err)
      let errorMessage = 'An error occurred'
      if (err instanceof Error)       errorMessage = err.message
      else if (typeof err === 'string') errorMessage = err
      else                              errorMessage = 'Failed to analyze food — please try again'
      setError(errorMessage)
    } finally {
      setIsAnalyzing(false)
    }
  }, [])

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
          <h1 className="text-4xl font-bold text-gray-900 mb-2">AI Food Recognition</h1>
          <p className="text-xl text-gray-600 mb-2">Indian Food Analysis with Nutrition Information</p>
          <div className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-primary-100 text-primary-800">
            AI-Powered Food Detection
          </div>
        </div>

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
                  <p className="mt-2 text-sm text-red-700">{error}</p>
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
              <ResultsPanel analysis={analysis} imageUrl={imageUrl} isLoading={isAnalyzing} />
            </div>
          )}
        </div>


      </div>
    </main>
  )
}
