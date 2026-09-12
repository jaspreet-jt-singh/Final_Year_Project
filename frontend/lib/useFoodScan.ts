'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { analyzeFood as requestAnalysis } from './endpoints'
import { ApiError } from './api'
import { createDraft, FoodAnalysis, MealDraft } from './meals'

export function useFoodScan() {
  const [analysis, setAnalysis] = useState<FoodAnalysis | null>(null)
  const [draft, setDraft] = useState<MealDraft | null>(null)
  const [imageUrl, setImageUrl] = useState<string | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [status, setStatus] = useState('')
  const running = useRef(false)
  const request = useRef<AbortController | null>(null)
  useEffect(() => () => { if (imageUrl) URL.revokeObjectURL(imageUrl) }, [imageUrl])
  useEffect(() => () => request.current?.abort(), [])

  const analyzeFood = useCallback(async (processed: File) => {
    if (running.current) return
    running.current = true
    request.current?.abort()
    const controller = new AbortController()
    request.current = controller
    setBusy(true); setError(''); setStatus(''); setAnalysis(null); setDraft(null)
    setFile(processed); setImageUrl(URL.createObjectURL(processed))
    try {
      const result = await requestAnalysis(processed, controller.signal)
      if (controller.signal.aborted) return
      setAnalysis(result)
      if (result.detections.length) {
        setDraft(createDraft(result, crypto.randomUUID()))
        setStatus(`Detected ${result.detections.length} Food Item${result.detections.length === 1 ? '' : 's'}. Review portions before saving.`)
      } else setStatus('No supported food was detected in this photo.')
    } catch (err) {
      if (!controller.signal.aborted) setError(err instanceof ApiError ? err.message : 'Could not analyze your photo. Please retry.')
    } finally { running.current = false; if (!controller.signal.aborted) setBusy(false) }
  }, [])
  const reset = () => { setAnalysis(null); setDraft(null); setImageUrl(null); setFile(null); setError(''); setStatus('') }
  return { analysis, draft, setDraft, imageUrl, file, busy, error, status, setStatus, analyzeFood, reset }
}
