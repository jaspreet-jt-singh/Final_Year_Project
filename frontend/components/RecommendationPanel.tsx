'use client'

import { Sparkles } from 'lucide-react'
import type { FoodAnalysis, MealDraft } from '@/lib/meals'
import { conditionOption } from '@/lib/goals'
import { useRecommendations } from '@/lib/useRecommendations'

export default function RecommendationPanel({ analysis, draft, goal, health }: { analysis: FoodAnalysis; draft: MealDraft; goal: string; health: string }) {
  const { state, option, retry } = useRecommendations(analysis, draft, goal, health)
  return <section className="panel guidance" aria-labelledby="guidance-heading">
    <div className="flex flex-wrap items-center gap-2 mb-3"><Sparkles size={20} /><h3 id="guidance-heading" className="font-semibold text-lg">A little food guidance</h3>
      {state.status === 'success' && <span className="pill" role="status">{conditionOption(state.condition).adjustment_label}</span>}
    </div>
    {state.status === 'loading' && <p role="status" className="muted">{option.key === 'none' ? 'Updating general nutrition guidance…' : `Updating for ${option.adjustment_label.replace('Adjusted for ', '')}…`}</p>}
    {state.status === 'error' && <div><p role="alert" className="notice">{state.error.message} Your food analysis is still available.</p>
      {state.error.retryAfter !== undefined && <p className="muted text-xs mt-2">Please wait about {state.error.retryAfter} seconds before retrying.</p>}
      <button className="btn-secondary mt-3" onClick={retry}>Retry guidance</button></div>}
    {state.status === 'idle' && <p className="muted">Include a food to see suggestions.</p>}
    {state.status === 'success' && <><ul className="space-y-3 list-disc pl-5">{state.recommendations.map((advice, i) => <li key={i} className="text-sm leading-relaxed">{advice}</li>)}</ul><p className="muted text-xs mt-4">{state.source === 'fallback' ? 'Local fallback suggestions' : 'AI-generated suggestions'} · {goal}</p></>}
    <p className="muted text-xs mt-4">General food-choice guidance, not portion-specific or medical advice. Consult a qualified professional for medical dietary needs.</p>
  </section>
}
