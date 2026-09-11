'use client'

import { GOALS } from '@/lib/meals'
import { useGoalSettings } from '@/lib/useGoalSettings'

export default function GoalSettings({ settings }: { settings: ReturnType<typeof useGoalSettings> }) {
  const { goalInput, setGoalInput, calorieInput, setCalorieInput, healthCondition, setHealthCondition, conditions, macros, goalError, macroError, applyGoals, ready } = settings
  return (<details className="panel compact"><summary>Goals & advanced settings</summary><p className="muted text-sm mt-3">Set your own daily target. These are general estimates, not prescribed dietary goals.</p>
          <form className="space-y-4 mt-5" onSubmit={event => { event.preventDefault(); applyGoals() }}>
            <label className="field">Your goal<select value={goalInput} onChange={e => setGoalInput(e.target.value)}>{GOALS.map(goal => <option key={goal}>{goal}</option>)}</select></label>
            <label className="field">Daily calorie target<input type="number" min="500" max="5000" step="1" required value={calorieInput} onChange={e => setCalorieInput(e.target.value)} /></label>
            <button className="btn-secondary" disabled={!ready}>Save goals</button>
          </form>
          {goalError && <p role="alert" className="notice mt-3">{goalError}</p>}
          <label className="field mt-5">Health context (this session only)<select value={healthCondition} onChange={e => setHealthCondition(e.target.value)}>{conditions.map(condition => <option key={condition.key} value={condition.key}>{condition.name}</option>)}</select></label>
          <p className="muted text-xs mt-2">This selection is sent to the recommendation service but is not saved in your browser history.</p>
          {macroError && <p role="alert" className="notice mt-3">{macroError}</p>}
          <p className="eyebrow mt-5 mb-2">Estimated daily macro targets</p><p className="text-sm">Protein {macros.protein_g} g · Carbs {macros.carbs_g} g · Fat {macros.fat_g} g</p>
        </details>)
}
