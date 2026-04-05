'use client'

import React, { useState } from 'react'
import ImageUpload from '@/components/ImageUpload'
import NutritionLabel from '@/components/NutritionLabel'
import ResultsPanel from '@/components/ResultsPanel'
import { Brain, Utensils } from 'lucide-react'

interface FoodAnalysis {
  food_label: string
  display_name: string
  confidence: number
  bounding_box: [number, number, number, number]
  img_width: number
  img_height: number
  macros: {
    calories: number
    protein_g: number
    carbs_g: number
    fat_g: number
  }
  macros_unit: string
  nutrition_source: string
  food_not_found: boolean
}

export default function Home() {
  const [analysis, setAnalysis] = useState<FoodAnalysis | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [imageUrl, setImageUrl] = useState<string | null>(null)

  const analyzeFood = async (file: File) => {
    setIsAnalyzing(true)
    setError(null)
    setAnalysis(null)
    setImageUrl(null)

    try {
      // Create image URL for preview
      const reader = new FileReader()
      reader.onload = (e) => {
        setImageUrl(e.target?.result as string)
      }
      reader.readAsDataURL(file)

      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch('http://localhost:8000/api/analyze-food', {
        method: 'POST',
        body: formData,
        // Don't set Content-Type header - let browser set it automatically for multipart forms
      })

      if (!response.ok) {
        let errorData
        try {
          errorData = await response.json()
        } catch (e) {
          errorData = { detail: `HTTP ${response.status}: ${response.statusText}` }
        }
        throw new Error(errorData.detail || `Failed to analyze food (${response.status})`)
      }

      const result = await response.json()
      setAnalysis(result)
    } catch (err) {
      console.error('Error analyzing food:', err)
      console.error('Error type:', typeof err)
      console.error('Error details:', JSON.stringify(err, null, 2))
      
      // Direct error display - force string conversion
      let errorMessage = 'An error occurred'
      if (err instanceof Error) {
        errorMessage = err.message
      } else if (typeof err === 'object' && err !== null) {
        // Force object to string conversion
        try {
          errorMessage = JSON.stringify(err)
        } catch (e) {
          errorMessage = String(err)
        }
        if (errorMessage === '{}') {
          errorMessage = 'Failed to analyze food - please try again'
        }
      } else if (typeof err === 'string') {
        errorMessage = err
      } else {
        errorMessage = String(err)
      }
      
      console.error('Final error message:', errorMessage)
      setError(errorMessage)
    } finally {
      setIsAnalyzing(false)
    }
  }

  const resetAnalysis = () => {
    setAnalysis(null)
    setError(null)
    setImageUrl(null)
  }

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
          
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            AI Food Recognition
          </h1>
          <p className="text-xl text-gray-600 mb-2">
            Indian Food Analysis with Nutrition Information
          </p>
          <div className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-primary-100 text-primary-800">
            Phase 2: Detection Overlay
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
                  <div className="mt-2 text-sm text-red-700">
                    <p>{error}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Main Content */}
        <div className="space-y-8">
          {/* Upload Section */}
          <div className="text-center">
            <h2 className="text-2xl font-semibold text-gray-900 mb-6">
              Upload Food Image
            </h2>
            <ImageUpload 
              onImageSelect={analyzeFood}
              isAnalyzing={isAnalyzing}
            />
          </div>

          {/* Results Section */}
          {(analysis || isAnalyzing) && (
            <div className="text-center">
              <div className="flex items-center justify-center space-x-4 mb-6">
                <h2 className="text-2xl font-semibold text-gray-900">
                  Analysis Results
                </h2>
                {!isAnalyzing && (
                  <button
                    onClick={resetAnalysis}
                    className="text-sm text-gray-600 hover:text-gray-800 underline"
                  >
                    Analyze another image
                  </button>
                )}
              </div>
              <ResultsPanel 
                analysis={analysis}
                imageUrl={imageUrl}
                isLoading={isAnalyzing}
              />
            </div>
          )}
        </div>

        {/* Footer Info */}
        <div className="mt-16 text-center">
          <div className="max-w-2xl mx-auto">
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">Phase 2 Features</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-gray-600">
                <div className="text-center">
                  <div className="font-medium text-gray-900 mb-1">Food Recognition</div>
                  <p>Identifies Indian dishes from uploaded images</p>
                </div>
                <div className="text-center">
                  <div className="font-medium text-gray-900 mb-1">Detection Overlay</div>
                  <p>Draws bounding boxes over detected food areas</p>
                </div>
                <div className="text-center">
                  <div className="font-medium text-gray-900 mb-1">Nutrition Analysis</div>
                  <p>Provides calories, protein, carbs, and fat</p>
                </div>
                <div className="text-center">
                  <div className="font-medium text-gray-900 mb-1">Mobile Responsive</div>
                  <p>Optimized layout for mobile devices</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}
