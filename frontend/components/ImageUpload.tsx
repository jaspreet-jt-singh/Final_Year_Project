'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { Camera, Upload } from 'lucide-react'
import { prepareImage } from '@/lib/prepareImage'

interface ImageUploadProps { onImageSelect: (file: File) => void; isAnalyzing: boolean; previewUrl: string | null; onReset: () => void }

export default function ImageUpload({ onImageSelect, isAnalyzing, previewUrl, onReset }: ImageUploadProps) {
  const input = useRef<HTMLInputElement>(null)
  const choose = useRef<HTMLButtonElement>(null)
  const processing = useRef(false)
  const mounted = useRef(true)
  const [preparing, setPreparing] = useState(false)
  const [error, setError] = useState('')
  const [dragging, setDragging] = useState(false)
  useEffect(() => { mounted.current = true; return () => { mounted.current = false } }, [])
  const processFile = useCallback(async (file: File) => {
    if (processing.current || isAnalyzing) return
    processing.current = true; setPreparing(true); setError('')
    try { const processed = await prepareImage(file); if (mounted.current) onImageSelect(processed) }
    catch (err) { if (mounted.current) setError(err instanceof Error ? err.message : 'Could not prepare the image.') }
    finally { processing.current = false; if (mounted.current) setPreparing(false) }
  }, [isAnalyzing, onImageSelect])
  const busy = preparing || isAnalyzing
  return <div>
    {error && <p role="alert" className="notice mb-4">{error}</p>}
    <input ref={input} type="file" accept="image/jpeg,image/png,image/webp" className="sr-only" tabIndex={-1} aria-label="Choose food image" disabled={busy}
      onChange={event => { const file = event.target.files?.[0]; if (file) void processFile(file); event.target.value = '' }} />
    {!previewUrl ? <div className={`upload-zone ${dragging ? 'dragging' : ''}`} onDragOver={event => { event.preventDefault(); if (!busy) setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={event => {
      event.preventDefault(); setDragging(false); const file = event.dataTransfer.files[0]; if (file) void processFile(file)
    }}>
      <div className="upload-icon"><Camera size={32} strokeWidth={1.5} /></div>
      <h3 className="text-xl font-semibold">What’s on your plate?</h3>
      <p className="muted text-sm mt-2 mb-6">Add a clear food photo. We’ll help with the details.</p>
      <button ref={choose} className="btn-primary" disabled={busy} onClick={() => input.current?.click()}><Upload size={18} />{preparing ? 'Preparing image…' : 'Choose Image'}</button>
      <p className="muted text-xs mt-4">Or drop a photo here · JPG, PNG, WebP</p>
    </div> : <div>
      <img src={previewUrl} alt="Selected food" className="rounded-2xl w-full max-h-80 object-contain bg-stone-100" />
      {!busy && <button className="btn-secondary mt-4" onClick={() => { setError(''); onReset(); requestAnimationFrame(() => choose.current?.focus()) }}>Choose another image</button>}
    </div>}
    {busy && <div role="status" className="mt-4 flex gap-3 items-start"><span className="loading-dot mt-1.5" /><div><p className="font-medium">{preparing ? 'Preparing your photo…' : 'Analyzing your food…'}</p><p className="muted text-sm">{preparing ? 'Resizing and checking orientation.' : 'The first analysis may take up to two minutes. Your saved meals are unchanged.'}</p></div></div>}
  </div>
}
