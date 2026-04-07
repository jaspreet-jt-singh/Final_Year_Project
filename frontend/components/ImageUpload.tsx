'use client'

import React, { useState, useCallback } from 'react'
import { Upload, X, Camera } from 'lucide-react'

interface ImageUploadProps {
  onImageSelect: (file: File) => void
  isAnalyzing: boolean
}

export default function ImageUpload({ onImageSelect, isAnalyzing }: ImageUploadProps) {
  const [isDragging, setIsDragging]     = useState(false)
  const [previewUrl, setPreviewUrl]     = useState<string | null>(null)
  // FIX: store raw File separately from preview URL
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

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
    const imageFile = Array.from(e.dataTransfer.files).find(f => f.type.startsWith('image/'))
    if (imageFile) processFile(imageFile)
  }, [])

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file && file.type.startsWith('image/')) processFile(file)
  }, [])

  const processFile = useCallback((file: File) => {
    // ✅ Preview via FileReader (display only — does NOT affect upload)
    const reader = new FileReader()
    reader.onload = (e) => setPreviewUrl(e.target?.result as string)
    reader.readAsDataURL(file)

    // ✅ Pass original raw File object to parent — never a canvas blob
    setSelectedFile(file)
    onImageSelect(file)
  }, [onImageSelect])

  const clearImage = useCallback(() => {
    setPreviewUrl(null)
    setSelectedFile(null)
  }, [])

  return (
    <div className="w-full">
      {!previewUrl ? (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors
            ${isDragging ? 'border-orange-400 bg-orange-50' : 'border-gray-300 hover:border-orange-300'}`}
        >
          <Upload className="mx-auto mb-4 text-gray-400" size={48} />
          <p className="text-gray-600 mb-4">Drag and drop an image here, or click to browse</p>
          <label className="cursor-pointer bg-orange-500 hover:bg-orange-600 text-white px-6 py-2 rounded-lg transition-colors">
            {isAnalyzing ? 'Analyzing...' : 'Choose Image'}
            <input
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleFileSelect}
              disabled={isAnalyzing}
            />
          </label>
        </div>
      ) : (
        <div className="relative">
          {!isAnalyzing && (
            <button
              onClick={clearImage}
              className="absolute top-2 right-2 z-10 bg-red-500 text-white rounded-full p-1 hover:bg-red-600"
            >
              <X size={16} />
            </button>
          )}
          {/* ✅ Preview uses FileReader URL — original File bytes are sent to API separately */}
          <img src={previewUrl} alt="Selected food" className="w-full rounded-xl object-contain max-h-80" />
          {isAnalyzing && (
            <div className="absolute inset-0 bg-black/40 flex items-center justify-center rounded-xl">
              <div className="text-white text-center">
                <Camera className="mx-auto mb-2 animate-pulse" size={32} />
                <p>Analyzing food...</p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
