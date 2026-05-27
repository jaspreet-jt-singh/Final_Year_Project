'use client'

import React from 'react'
import { Zap, Activity, TrendingUp, Droplet } from 'lucide-react'

interface NutritionLabelProps {
  macros: {
    calories: number
    protein_g: number
    carbs_g: number
    fat_g: number
  }
  showTitle?: boolean
}

export default function NutritionLabel({ macros, showTitle = false }: NutritionLabelProps) {
  return (
    <div className="space-y-3">
      {showTitle && (
        <h4 className="text-sm font-semibold text-gray-700 uppercase tracking-wider">Nutrition per 100g</h4>
      )}
      <div className="grid grid-cols-4 gap-2">
        <div className="text-center p-3 bg-orange-50 rounded-xl">
          <Zap className="w-5 h-5 text-orange-600 mx-auto mb-1" />
          <div className="text-xl font-bold text-gray-900">
            {Math.round(macros.calories)}
          </div>
          <div className="text-[10px] text-gray-500 font-medium">CAL</div>
        </div>
        
        <div className="text-center p-3 bg-blue-50 rounded-xl">
          <Activity className="w-5 h-5 text-blue-600 mx-auto mb-1" />
          <div className="text-xl font-bold text-gray-900">
            {Math.round(macros.protein_g)}g
          </div>
          <div className="text-[10px] text-gray-500 font-medium">PROTEIN</div>
        </div>
        
        <div className="text-center p-3 bg-green-50 rounded-xl">
          <TrendingUp className="w-5 h-5 text-green-600 mx-auto mb-1" />
          <div className="text-xl font-bold text-gray-900">
            {Math.round(macros.carbs_g)}g
          </div>
          <div className="text-[10px] text-gray-500 font-medium">CARBS</div>
        </div>

        <div className="text-center p-3 bg-purple-50 rounded-xl">
          <Droplet className="w-5 h-5 text-purple-600 mx-auto mb-1" />
          <div className="text-xl font-bold text-gray-900">
            {Math.round(macros.fat_g)}g
          </div>
          <div className="text-[10px] text-gray-500 font-medium">FAT</div>
        </div>
      </div>
    </div>
  )
}
