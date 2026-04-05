'use client'

import React from 'react'
import { Zap, Activity, TrendingUp } from 'lucide-react'

interface NutritionLabelProps {
  macros: {
    calories: number
    protein_g: number
    carbs_g: number
    fat_g: number
  }
}

export default function NutritionLabel({ macros }: NutritionLabelProps) {
  return (
    <div className="grid grid-cols-3 gap-4">
      <div className="text-center p-4 bg-orange-50 rounded-lg">
        <Zap className="w-6 h-6 text-orange-600 mx-auto mb-2" />
        <div className="text-2xl font-bold text-gray-900">
          {macros.calories}
        </div>
        <div className="text-sm text-gray-600">Calories</div>
      </div>
      
      <div className="text-center p-4 bg-blue-50 rounded-lg">
        <Activity className="w-6 h-6 text-blue-600 mx-auto mb-2" />
        <div className="text-2xl font-bold text-gray-900">
          {macros.protein_g}g
        </div>
        <div className="text-sm text-gray-600">Protein</div>
      </div>
      
      <div className="text-center p-4 bg-yellow-50 rounded-lg">
        <TrendingUp className="w-6 h-6 text-yellow-600 mx-auto mb-2" />
        <div className="text-2xl font-bold text-gray-900">
          {macros.carbs_g}g
        </div>
        <div className="text-sm text-gray-600">Carbs</div>
      </div>
    </div>
  )
}
