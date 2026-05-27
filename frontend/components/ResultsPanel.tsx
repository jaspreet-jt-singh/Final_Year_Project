'use client'

import React, { useState, useEffect } from 'react'
import { CheckCircle, AlertCircle, TrendingUp, Activity, Zap, Sparkles, Loader2 } from 'lucide-react'
import NutritionLabel from './NutritionLabel'
import ImageOverlay from './ImageOverlay'

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
}

interface ResultsPanelProps {
  analysis: FoodAnalysis | null
  imageUrl: string | null
  isLoading: boolean
  userGoal?: string
}

export default function ResultsPanel({ analysis, imageUrl, isLoading, userGoal = 'Maintenance' }: ResultsPanelProps) {
  // Phase 3: AI Recommendations state
  const [recommendations, setRecommendations] = useState<string[]>([])
  const [isLoadingRecommendations, setIsLoadingRecommendations] = useState(false)
  const [recommendationSource, setRecommendationSource] = useState<string>('')
  // Fetch AI recommendations when analysis is complete
  useEffect(() => {
    if (analysis && analysis.detections && analysis.detections.length > 0 && !isLoading) {
      fetchRecommendations()
    }
  }, [analysis, isLoading])

  const fetchRecommendations = async () => {
    if (!analysis || !analysis.detections || analysis.detections.length === 0) return
    
    setIsLoadingRecommendations(true)
    setRecommendations([])
    
    try {
      const response = await fetch('http://localhost:8000/api/recommendations', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          detected_foods: analysis.detections,
          user_goal: userGoal
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        setRecommendations(data.recommendations || [])
        setRecommendationSource(data.source || 'unknown')
      }
    } catch (err) {
      console.error('Failed to fetch recommendations:', err)
    } finally {
      setIsLoadingRecommendations(false)
    }
  }

  if (isLoading) {
    return (
      <div className="w-full max-w-2xl mx-auto">
        <div className="card">
          <div className="animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-3/4 mb-4"></div>
            <div className="h-3 bg-gray-200 rounded w-1/2 mb-6"></div>
            <div className="grid grid-cols-4 gap-4">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-16 bg-gray-200 rounded"></div>
              ))}
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (!analysis || !analysis.detections || analysis.detections.length === 0) {
    return null
  }

  // Format YOLO label for display (gulabjamun → Gulab Jamun, paneerKheer → Paneer Kheer)
  const formatYoloLabel = (label: string): string => {
    // Insert space before uppercase letters (camelCase → camel Case)
    let formatted = label.replace(/([a-z])([A-Z])/g, '$1 $2')
    // Replace underscores with spaces (snake_case → snake case)
    formatted = formatted.replace(/_/g, ' ')
    // Title case
    return formatted.replace(/\w\S*/g, (txt) => 
      txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase()
    )
  }

  const getConfidenceBadge = (confidence: number) => {
    if (confidence >= 0.8) return 'bg-green-100 text-green-600'
    if (confidence >= 0.6) return 'bg-yellow-100 text-yellow-600'
    return 'bg-red-100 text-red-600'
  }

  return (
    <div className="w-full max-w-2xl mx-auto space-y-6">
      {/* Summary */}
      <div className="card">
        <h3 className="text-xl font-bold text-gray-900 mb-2">
          Detected {analysis.detections.length} Food Item{analysis.detections.length > 1 ? 's' : ''}
        </h3>
      </div>

      {/* Image with ALL Detection Overlays */}
      {imageUrl && analysis.img_width && analysis.img_height && (
        <div className="card">
          <h3 className="text-lg font-bold text-gray-900 mb-4">Food Detection</h3>
          <div className="relative">
            <img 
              src={imageUrl} 
              alt="Detected foods"
              className="w-full rounded-lg"
            />
            {/* Bounding boxes overlay */}
            {analysis.detections.map((det, idx) => (
              <div
                key={idx}
                className="absolute border-2 border-blue-500 rounded pointer-events-none"
                style={{
                  left: `${(det.bounding_box[0] / analysis.img_width!) * 100}%`,
                  top: `${(det.bounding_box[1] / analysis.img_height!) * 100}%`,
                  width: `${((det.bounding_box[2] - det.bounding_box[0]) / analysis.img_width!) * 100}%`,
                  height: `${((det.bounding_box[3] - det.bounding_box[1]) / analysis.img_height!) * 100}%`,
                }}
              >
                <span className="absolute -top-6 left-0 bg-blue-500 text-white text-xs px-2 py-1 rounded whitespace-nowrap">
                  {formatYoloLabel(det.food_label)} ({(det.confidence * 100).toFixed(0)}%)
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Each Detected Food */}
      {analysis.detections.map((detection, index) => (
        <div key={index} className="bg-white rounded-2xl shadow-md border border-gray-100 p-6 text-left">
          {/* Detection Header */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-3">
              <span className="bg-gradient-to-br from-orange-400 to-amber-500 text-white w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm shadow-md">
                {index + 1}
              </span>
              <div>
                <h3 className="text-xl font-semibold text-gray-900">
                  {formatYoloLabel(detection.food_label)}
                </h3>
                <p className="text-sm text-gray-500">
                  {detection.display_name !== formatYoloLabel(detection.food_label) && (
                    <span>{detection.display_name} · </span>
                  )}
                  <span className="text-gray-400">per 100g</span>
                </p>
              </div>
            </div>
            <div className={`px-3 py-1 rounded-full text-sm font-semibold ${getConfidenceBadge(detection.confidence)}`}>
              {(detection.confidence * 100).toFixed(0)}%
            </div>
          </div>

          {/* Nutrition or Not Found */}
          {!detection.nutrition_not_found && detection.macros ? (
            <NutritionLabel macros={detection.macros} />
          ) : (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
              <div className="flex items-center space-x-2">
                <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0" />
                <span className="text-sm text-amber-800">
                  Nutrition data not available for {formatYoloLabel(detection.food_label)}
                </span>
              </div>
            </div>
          )}

          <div className="mt-4 pt-3 border-t border-gray-100 flex items-center space-x-4 text-xs text-gray-400">
            <span>Source: {detection.nutrition_source || 'N/A'}</span>
            <span>•</span>
            <span>Confidence: {(detection.confidence * 100).toFixed(1)}%</span>
          </div>
        </div>
      ))}

      {/* Phase 3: AI Dietary Guidance */}
      <div className="card bg-gradient-to-br from-purple-50 to-indigo-50 border-purple-200">
        <div className="flex items-center mb-4">
          <Sparkles className="w-6 h-6 text-purple-600 mr-2" />
          <h3 className="text-xl font-bold text-gray-900">AI Dietary Guidance</h3>
        </div>
        
        {isLoadingRecommendations ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-8 h-8 text-purple-600 animate-spin" />
            <span className="ml-3 text-gray-600">Generating personalized advice...</span>
          </div>
        ) : recommendations.length > 0 ? (
          <div className="space-y-3">
            {recommendations.map((rec, idx) => (
              <div key={idx} className="flex items-start space-x-3">
                <div className="flex-shrink-0 w-6 h-6 bg-purple-100 rounded-full flex items-center justify-center mt-0.5">
                  <span className="text-purple-600 text-sm font-medium">{idx + 1}</span>
                </div>
                <p className="text-gray-700 flex-1">{rec}</p>
              </div>
            ))}
            <div className="mt-4 pt-3 border-t border-purple-200">
              <p className="text-xs text-gray-500">
                Powered by AI • Goal: {userGoal}
              </p>
            </div>
          </div>
        ) : (
          <div className="text-center py-6 text-gray-500">
            <p>Unable to generate recommendations at this time.</p>
            <p className="text-sm mt-1">Your goal: {userGoal}</p>
          </div>
        )}
      </div>
    </div>
  )
}
