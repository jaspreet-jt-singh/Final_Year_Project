'use client'

import React from 'react'
import { CheckCircle, AlertCircle, TrendingUp, Activity, Zap } from 'lucide-react'
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

  if (!analysis || !analysis.detections || analysis.detections.length === 0) {
    return null
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
        <p className="text-sm text-gray-600">
          Image size: {analysis.img_width} × {analysis.img_height}
        </p>
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
                  {det.display_name} ({(det.confidence * 100).toFixed(0)}%)
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Each Detected Food */}
      {analysis.detections.map((detection, index) => (
        <div key={index} className="card">
          {/* Detection Header */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-3">
              <span className="bg-primary-100 text-primary-800 w-8 h-8 rounded-full flex items-center justify-center font-bold">
                {index + 1}
              </span>
              <div>
                <h3 className="text-xl font-semibold text-gray-900">{detection.display_name}</h3>
                <p className="text-sm text-gray-600">Label: {detection.food_label}</p>
              </div>
            </div>
            <div className={`px-3 py-1 rounded-full text-sm font-medium ${getConfidenceBadge(detection.confidence)}`}>
              {(detection.confidence * 100).toFixed(1)}%
            </div>
          </div>

          {/* Nutrition or Not Found */}
          {!detection.nutrition_not_found && detection.macros ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center p-4 bg-orange-50 rounded-lg">
                <Zap className="w-6 h-6 text-orange-600 mx-auto mb-2" />
                <div className="text-2xl font-bold text-gray-900">
                  {Math.round(detection.macros.calories)}
                </div>
                <div className="text-sm text-gray-600">Calories</div>
              </div>
              
              <div className="text-center p-4 bg-blue-50 rounded-lg">
                <Activity className="w-6 h-6 text-blue-600 mx-auto mb-2" />
                <div className="text-2xl font-bold text-gray-900">
                  {Math.round(detection.macros.protein_g)}g
                </div>
                <div className="text-sm text-gray-600">Protein</div>
              </div>
              
              <div className="text-center p-4 bg-green-50 rounded-lg">
                <div className="w-6 h-6 bg-green-600 rounded-full mx-auto mb-2"></div>
                <div className="text-2xl font-bold text-gray-900">
                  {Math.round(detection.macros.carbs_g)}g
                </div>
                <div className="text-sm text-gray-600">Carbs</div>
              </div>
              
              <div className="text-center p-4 bg-purple-50 rounded-lg">
                <div className="w-6 h-6 bg-purple-600 rounded-full mx-auto mb-2"></div>
                <div className="text-2xl font-bold text-gray-900">
                  {Math.round(detection.macros.fat_g)}g
                </div>
                <div className="text-sm text-gray-600">Fat</div>
              </div>
            </div>
          ) : (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-center space-x-2">
                <AlertCircle className="w-5 h-5 text-red-600" />
                <span className="font-medium text-red-800">
                  Nutrition data not available for {detection.display_name}
                </span>
              </div>
            </div>
          )}

          <div className="mt-4 flex items-center space-x-4 text-sm text-gray-600">
            <span>Source: {detection.nutrition_source || 'N/A'}</span>
            <span>•</span>
            <span>Unit: {detection.macros_unit}</span>
          </div>
        </div>
      ))}
    </div>
  )
}
