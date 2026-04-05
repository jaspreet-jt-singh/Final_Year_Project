'use client'

import React, { useState, useCallback } from 'react'
import { Upload, X, Camera } from 'lucide-react'

interface ImageUploadProps {
  onImageSelect: (file: File) => void
  isAnalyzing: boolean
}

export default function ImageUpload({ onImageSelect, isAnalyzing }: ImageUploadProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [selectedImage, setSelectedImage] = useState<string | null>(null)

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    
    const files = Array.from(e.dataTransfer.files)
    const imageFile = files.find(file => file.type.startsWith('image/'))
    
    if (imageFile) {
      handleImageSelect(imageFile)
    }
  }, [])

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file && file.type.startsWith('image/')) {
      handleImageSelect(file)
    }
  }, [])

  const handleImageSelect = useCallback((file: File) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      setSelectedImage(e.target?.result as string)
      onImageSelect(file)
    }
    reader.readAsDataURL(file)
  }, [onImageSelect])

  const clearImage = useCallback(() => {
    setSelectedImage(null)
  }, [])

  return (
    <div className="w-full max-w-2xl mx-auto">
      {!selectedImage ? (
        <div
          className={`relative border-3 border-dashed rounded-xl p-8 text-center transition-all ${
            isDragging
              ? 'border-primary-500 bg-primary-50'
              : 'border-gray-300 hover:border-gray-400 bg-white'
          } ${isAnalyzing ? 'opacity-50 pointer-events-none' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <input
            type="file"
            accept="image/*"
            onChange={handleFileSelect}
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            disabled={isAnalyzing}
          />
          
          <div className="flex flex-col items-center space-y-4">
            <div className={`p-4 rounded-full ${isDragging ? 'bg-primary-100' : 'bg-gray-100'}`}>
              <Camera className={`w-8 h-8 ${isDragging ? 'text-primary-600' : 'text-gray-600'}`} />
            </div>
            
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-1">
                Upload Food Image
              </h3>
              <p className="text-gray-600 text-sm">
                Drag and drop an image here, or click to browse
              </p>
            </div>
            
            <button
              type="button"
              className="btn-primary"
              disabled={isAnalyzing}
            >
              {isAnalyzing ? 'Analyzing...' : 'Choose Image'}
            </button>
          </div>
        </div>
      ) : (
        <div className="relative">
          <div className="card">
            <div className="relative">
              <img
                src={selectedImage}
                alt="Uploaded food"
                className="w-full h-64 object-cover rounded-lg"
              />
              
              {!isAnalyzing && (
                <button
                  onClick={clearImage}
                  className="absolute top-2 right-2 p-2 bg-white rounded-full shadow-lg hover:bg-gray-100 transition-colors"
                >
                  <X className="w-4 h-4 text-gray-600" />
                </button>
              )}
              
              {isAnalyzing && (
                <div className="absolute inset-0 bg-black bg-opacity-50 rounded-lg flex items-center justify-center">
                  <div className="text-white text-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white mx-auto mb-2"></div>
                    <p className="text-sm">Analyzing food...</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
