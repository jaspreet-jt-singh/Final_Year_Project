'use client'

import React from 'react'
import { CheckCircle, AlertCircle, TrendingUp, Activity, Zap } from 'lucide-react'
import ImageOverlay from './ImageOverlay'

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

interface ResultsPanelProps {
  analysis: FoodAnalysis | null
  imageUrl: string | null
  isLoading: boolean
}

export default function ResultsPanel({ analysis, imageUrl, isLoading }: ResultsPanelProps) {
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

  if (!analysis) {
    return null
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600'
    if (confidence >= 0.6) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getConfidenceBg = (confidence: number) => {
    if (confidence >= 0.8) return 'bg-green-100'
    if (confidence >= 0.6) return 'bg-yellow-100'
    return 'bg-red-100'
  }

  return (
    <div className="w-full max-w-2xl mx-auto space-y-6">
      {/* Detection Results */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-semibold text-gray-900">Food Detection</h3>
          <div className={`px-3 py-1 rounded-full text-sm font-medium ${getConfidenceBg(analysis.confidence)} ${getConfidenceColor(analysis.confidence)}`}>
            {(analysis.confidence * 100).toFixed(1)}% confidence
          </div>
        </div>

        {/* Image with Overlay */}
        {imageUrl && analysis.bounding_box && (
          <div className="mb-6">
            <ImageOverlay
              imageUrl={imageUrl}
              boundingBox={analysis.bounding_box}
              confidence={analysis.confidence}
              foodLabel={analysis.display_name}
            />
          </div>
        )}

        {/* Detection Info */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex items-center space-x-2 mb-2">
              <CheckCircle className="w-5 h-5 text-green-600" />
              <span className="font-medium text-gray-900">Detected Food</span>
            </div>
            <p className="text-2xl font-bold text-gray-900">{analysis.display_name}</p>
            <p className="text-sm text-gray-600">Label: {analysis.food_label}</p>
          </div>
          
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex items-center space-x-2 mb-2">
              <Activity className="w-5 h-5 text-blue-600" />
              <span className="font-medium text-gray-900">Detection Confidence</span>
            </div>
            <p className={`text-2xl font-bold ${getConfidenceColor(analysis.confidence)}`}>
              {(analysis.confidence * 100).toFixed(1)}%
            </p>
            <p className="text-sm text-gray-600">
              {analysis.confidence >= 0.8 ? 'High confidence' : 
               analysis.confidence >= 0.6 ? 'Medium confidence' : 'Low confidence'}
            </p>
          </div>
        </div>
      </div>

      {/* Nutrition Results */}
      {!analysis.food_not_found && analysis.macros && (
        <div className="card">
          <div className="flex items-center space-x-2 mb-4">
            <TrendingUp className="w-5 h-5 text-green-600" />
            <h3 className="text-xl font-semibold text-gray-900">Nutrition Information</h3>
            <span className="text-sm text-gray-600">({analysis.macros_unit})</span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-orange-50 rounded-lg p-4 text-center">
              <div className="text-3xl font-bold text-orange-600">
                {Math.round(analysis.macros.calories)}
              </div>
              <div className="text-sm font-medium text-gray-700">Calories</div>
            </div>
            
            <div className="bg-blue-50 rounded-lg p-4 text-center">
              <div className="text-3xl font-bold text-blue-600">
                {Math.round(analysis.macros.protein_g)}
              </div>
              <div className="text-sm font-medium text-gray-700">Protein (g)</div>
            </div>
            
            <div className="bg-green-50 rounded-lg p-4 text-center">
              <div className="text-3xl font-bold text-green-600">
                {Math.round(analysis.macros.carbs_g)}
              </div>
              <div className="text-sm font-medium text-gray-700">Carbs (g)</div>
            </div>
            
            <div className="bg-purple-50 rounded-lg p-4 text-center">
              <div className="text-3xl font-bold text-purple-600">
                {Math.round(analysis.macros.fat_g)}
              </div>
              <div className="text-sm font-medium text-gray-700">Fat (g)</div>
            </div>
          </div>

          <div className="mt-4 p-4 bg-gray-50 rounded-lg">
            <div className="flex items-center space-x-2">
              <Zap className="w-5 h-5 text-yellow-600" />
              <span className="font-medium text-gray-900">Source</span>
            </div>
            <p className="text-sm text-gray-600">
              Nutrition data from {analysis.nutrition_source} database
            </p>
          </div>
        </div>
      )}

      {/* Food Not Found */}
      {analysis.food_not_found && (
        <div className="card">
          <div className="flex items-center space-x-2 mb-4">
            <AlertCircle className="w-5 h-5 text-red-600" />
            <h3 className="text-xl font-semibold text-gray-900">Nutrition Information</h3>
          </div>
          
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="text-center">
              <div className="text-lg font-medium text-red-800 mb-2">
                "{analysis.display_name}" not found in nutrition database
              </div>
              <p className="text-sm text-red-700">
                This food is not currently in our Indian nutrition database.
              </p>
              <p className="text-sm text-red-700 mt-2">
                Known missing foods: kathi_roll, vada_pav, momos
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
