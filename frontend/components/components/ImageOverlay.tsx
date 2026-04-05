'use client'

import React, { useRef, useEffect, useState } from 'react'
import { Box } from 'lucide-react'

interface BoundingBox {
  x: number
  y: number
  width: number
  height: number
}

interface ImageOverlayProps {
  imageUrl: string
  boundingBox: [number, number, number, number] // [x1, y1, x2, y2]
  confidence: number
  foodLabel: string
}

export default function ImageOverlay({ imageUrl, boundingBox, confidence, foodLabel }: ImageOverlayProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [imageSize, setImageSize] = useState({ width: 0, height: 0 })
  const [canvasSize, setCanvasSize] = useState({ width: 0, height: 0 })

  useEffect(() => {
    const img = new Image()
    img.onload = () => {
      setImageSize({ width: img.width, height: img.height })
    }
    img.src = imageUrl
  }, [imageUrl])

  useEffect(() => {
    if (!canvasRef.current || !imageSize.width) return

    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Set canvas size to match display size
    const rect = canvas.getBoundingClientRect()
    setCanvasSize({ width: rect.width, height: rect.height })

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    // Calculate scale factors
    const scaleX = canvas.width / imageSize.width
    const scaleY = canvas.height / imageSize.height

    // Draw bounding box
    const [x1, y1, x2, y2] = boundingBox
    const scaledX1 = x1 * scaleX
    const scaledY1 = y1 * scaleY
    const scaledX2 = x2 * scaleX
    const scaledY2 = y2 * scaleY

    // Draw box
    ctx.strokeStyle = '#10b981' // green-600
    ctx.lineWidth = 3
    ctx.strokeRect(scaledX1, scaledY1, scaledX2 - scaledX1, scaledY2 - scaledY1)

    // Draw label background
    const text = `${foodLabel} (${(confidence * 100).toFixed(1)}%)`
    ctx.font = 'bold 16px system-ui'
    const textMetrics = ctx.measureText(text)
    const textWidth = textMetrics.width
    const textHeight = 20

    // Position label above box
    const labelX = scaledX1
    const labelY = scaledY1 - textHeight - 5

    // Draw label background
    ctx.fillStyle = '#10b981' // green-600
    ctx.fillRect(labelX - 2, labelY - textHeight, textWidth + 4, textHeight + 4)

    // Draw label text
    ctx.fillStyle = 'white'
    ctx.fillText(text, labelX, labelY)

  }, [boundingBox, confidence, foodLabel, imageSize, canvasSize])

  return (
    <div className="relative w-full">
      <img
        src={imageUrl}
        alt="Detected food"
        className="w-full h-auto rounded-lg shadow-lg"
        style={{ maxHeight: '500px', objectFit: 'contain' }}
      />
      <canvas
        ref={canvasRef}
        width={canvasSize.width || 0}
        height={canvasSize.height || 0}
        className="absolute top-0 left-0 w-full h-full pointer-events-none"
        style={{ mixBlendMode: 'multiply' }}
      />
    </div>
  )
}
