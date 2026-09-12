'use client'

import { useId, useImperativeHandle, useRef, useState, type Ref } from 'react'
import { alphabeticalFoods, searchSupportedFoods, supportedFoodExamples } from '@/lib/supportedFoods'

export type SupportedFoodsHandle = { openAndFocus: () => void }

export default function SupportedFoods({ ref }: { ref?: Ref<SupportedFoodsHandle> }) {
  const id = useId()
  const disclosure = useRef<HTMLDetailsElement>(null)
  const search = useRef<HTMLInputElement>(null)
  const [query, setQuery] = useState('')
  const matches = searchSupportedFoods(query)
  const count = alphabeticalFoods.length

  useImperativeHandle(ref, () => ({
    openAndFocus() {
      setQuery('')
      if (disclosure.current) disclosure.current.open = true
      search.current?.focus({ preventScroll: true })
      search.current?.scrollIntoView({ block: 'nearest', behavior: 'auto' })
    },
  }), [])

  return <div className="supported-foods mb-5">
    <p className="font-semibold text-sm">Trained to recognize {count} food categories.</p>
    <p className="muted text-sm mt-2">Check the supported foods before uploading. Foods outside this list may not be recognized, and recognition can sometimes miss listed foods.</p>
    <p className="muted text-xs mt-3">Examples: {supportedFoodExamples.map(food => food.name).join(', ')}.</p>
    <details ref={disclosure} className="mt-3">
      <summary className="text-sm py-2">View all {count} supported foods</summary>
      <div className="mt-3">
        <label className="field" htmlFor={`${id}-search`}>Search supported foods
          <input ref={search} id={`${id}-search`} type="search" value={query} onChange={event => setQuery(event.target.value)} aria-describedby={`${id}-count`} autoComplete="off" />
        </label>
        <div className="flex flex-wrap items-center justify-between gap-2 my-2">
          <p id={`${id}-count`} role="status" aria-live="polite" aria-atomic="true" className="muted text-xs">{matches.length} of {count} categories</p>
          <button type="button" className="text-button" disabled={!query} onClick={() => { setQuery(''); search.current?.focus() }}>Clear search</button>
        </div>
        {matches.length ? <ul className="supported-food-list" tabIndex={0} aria-label="Supported food categories">
          {matches.map(food => <li key={food.id}>{food.name}</li>)}
        </ul> : <p className="muted text-sm">No supported categories match your search. Try another spelling or clear the search to browse all foods.</p>}
        <p className="muted text-xs mt-3">These are model categories, not coverage of every recipe or variation.</p>
      </div>
    </details>
  </div>
}
