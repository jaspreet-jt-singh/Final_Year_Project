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

  const getConfidenceText = (confidence: number) => {
    if (confidence >= 0.8) return 'High Confidence'
    if (confidence >= 0.6) return 'Medium Confidence'
    return 'Low Confidence'
  }

  return (
    <div className="w-full max-w-2xl mx-auto space-y-6">
      {/* Image with Detection Overlay */}
      {imageUrl && analysis.bounding_box && (
        <div className="card">
          <h3 className="text-lg font-bold text-gray-900 mb-4">Food Detection</h3>
          <ImageOverlay
            imageUrl={imageUrl}
            boundingBox={analysis.bounding_box}
            confidence={analysis.confidence}
            foodLabel={analysis.display_name}
          />
        </div>
      )}

      {/* Detection Info */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-semibold text-gray-900">Detection Results</h3>
          <div className={`px-3 py-1 rounded-full text-sm font-medium ${
            analysis.confidence >= 0.8 ? 'bg-green-100 text-green-600' :
            analysis.confidence >= 0.6 ? 'bg-yellow-100 text-yellow-600' :
            'bg-red-100 text-red-600'
          }`}>
            {(analysis.confidence * 100).toFixed(1)}% confidence
          </div>
        </div>

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
            <p className={`text-2xl font-bold ${
              analysis.confidence >= 0.8 ? 'text-green-600' :
              analysis.confidence >= 0.6 ? 'text-yellow-600' :
              'text-red-600'
            }`}>
              {(analysis.confidence * 100).toFixed(1)}%
            </p>
            <p className="text-sm text-gray-600">
              {analysis.confidence >= 0.8 ? 'High confidence' : 
               analysis.confidence >= 0.6 ? 'Medium confidence' : 'Low confidence'}
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-4 text-sm text-gray-600">
          <span>Source: {analysis.nutrition_source}</span>
          <span>•</span>
          <span>Unit: {analysis.macros_unit}</span>
        </div>
      </div>

      {/* Nutrition Information */}
      <div className="card">
        <h3 className="text-xl font-bold text-gray-900 mb-6">Nutrition Information</h3>
        
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="text-center p-4 bg-orange-50 rounded-lg">
            <Zap className="w-6 h-6 text-orange-600 mx-auto mb-2" />
            <div className="text-2xl font-bold text-gray-900">
              {analysis.macros.calories}
            </div>
            <div className="text-sm text-gray-600">Calories</div>
          </div>
          
          <div className="text-center p-4 bg-blue-50 rounded-lg">
            <Activity className="w-6 h-6 text-blue-600 mx-auto mb-2" />
            <div className="text-2xl font-bold text-gray-900">
              {analysis.macros.protein_g}g
            </div>
            <div className="text-sm text-gray-600">Protein</div>
          </div>
          
          <div className="text-center p-4 bg-yellow-50 rounded-lg">
            <TrendingUp className="w-6 h-6 text-yellow-600 mx-auto mb-2" />
            <div className="text-2xl font-bold text-gray-900">
              {analysis.macros.carbs_g}g
            </div>
            <div className="text-sm text-gray-600">Carbs</div>
          </div>
          
          <div className="text-center p-4 bg-green-50 rounded-lg">
            <div className="w-6 h-6 bg-green-600 rounded-full mx-auto mb-2"></div>
            <div className="text-2xl font-bold text-gray-900">
              {analysis.macros.fat_g}g
            </div>
            <div className="text-sm text-gray-600">Fat</div>
          </div>
        </div>

        {/* Macronutrient Breakdown */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700">Protein</span>
            <span className="text-sm text-gray-600">{analysis.macros.protein_g}g</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-blue-600 h-2 rounded-full"
              style={{ width: `${Math.min((analysis.macros.protein_g / 25) * 100, 100)}%` }}
            ></div>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700">Carbohydrates</span>
            <span className="text-sm text-gray-600">{analysis.macros.carbs_g}g</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-yellow-600 h-2 rounded-full"
              style={{ width: `${Math.min((analysis.macros.carbs_g / 50) * 100, 100)}%` }}
            ></div>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700">Fat</span>
            <span className="text-sm text-gray-600">{analysis.macros.fat_g}g</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-green-600 h-2 rounded-full"
              style={{ width: `${Math.min((analysis.macros.fat_g / 30) * 100, 100)}%` }}
            ></div>
          </div>
        </div>
      </div>

      </div>
  )
}
