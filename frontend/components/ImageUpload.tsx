'use client'

import React, { useState, useCallback, useEffect, useRef } from 'react'
import { Upload, X, Camera } from 'lucide-react'
import { prepareImage } from '@/lib/prepareImage'

interface ImageUploadProps {
  onImageSelect: (file: File) => void
  isAnalyzing: boolean
}

export default function ImageUpload({ onImageSelect, isAnalyzing }: ImageUploadProps) {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [preparing, setPreparing] = useState(false)
  const [error, setError] = useState('')
  const processing = useRef(false)
  useEffect(() => () => { if (previewUrl) URL.revokeObjectURL(previewUrl) }, [previewUrl])
  const processFile = useCallback(async (file: File) => {
    if (processing.current || isAnalyzing) return
    processing.current = true
    setPreparing(true)
    setError('')
    try {
      const processed = await prepareImage(file)
      setPreviewUrl(URL.createObjectURL(processed))
      onImageSelect(processed)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not prepare the image.')
    } finally {
      processing.current = false
      setPreparing(false)
    }
  }, [isAnalyzing, onImageSelect])
  const busy = preparing || isAnalyzing
  return (
    <div className="w-full">
      {error && <p role="alert" className="text-red-600 mb-3">{error}</p>}
      {!previewUrl ? (
        <div onDragOver={e => e.preventDefault()} onDrop={e => {
          e.preventDefault()
          const file = e.dataTransfer.files[0]
          if (file) void processFile(file)
        }} className="border-2 border-dashed rounded-xl p-8 text-center border-gray-300">
          <Upload className="mx-auto mb-4 text-gray-400" size={48} />
          <p className="text-gray-600 mb-4">Drag and drop an image here, or click to browse</p>
          <label className="cursor-pointer bg-orange-500 text-white px-6 py-2 rounded-lg">
            {busy ? 'Preparing image...' : 'Choose Image'}
            <input type="file" accept="image/jpeg,image/png,image/webp" className="hidden" disabled={busy}
              onChange={e => { const file = e.target.files?.[0]; if (file) void processFile(file); e.target.value = '' }} />
          </label>
        </div>
      ) : (
        <div className="relative">
          {!busy && <button aria-label="Choose another image" onClick={() => setPreviewUrl(null)}
            className="absolute top-2 right-2 z-10 bg-red-500 text-white rounded-full p-1"><X size={16} /></button>}
          <img src={previewUrl} alt="Selected food" className="w-full rounded-xl object-contain max-h-80" />
          {busy && <div className="absolute inset-0 bg-black/40 flex items-center justify-center rounded-xl">
            <div className="text-white text-center"><Camera className="mx-auto mb-2 animate-pulse" size={32} />
              <p>Analyzing food...</p><p className="text-sm">The first analysis may take up to two minutes.</p>
            </div></div>}
        </div>
      )}
    </div>
  )
}
