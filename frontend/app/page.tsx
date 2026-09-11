'use client'

import { ArrowRight, Leaf, Utensils } from 'lucide-react'
import ImageUpload from '@/components/ImageUpload'
import ResultsPanel from '@/components/ResultsPanel'
import MealHistory from '@/components/MealHistory'
import DailySummary from '@/components/DailySummary'
import GoalSettings from '@/components/GoalSettings'
import { useFoodScan } from '@/lib/useFoodScan'
import { useGoalSettings } from '@/lib/useGoalSettings'
import { useMealJournal } from '@/lib/useMealJournal'

export default function Home() {
  const scan = useFoodScan()
  const { analysis, draft, setDraft, imageUrl, file, busy, error, status, setStatus, analyzeFood, reset } = scan
  const meals = useMealJournal(draft, setDraft, setStatus)
  const { journal, commit, ready, today, storageError, deleted, setDeleted, todaysMeals, daily, saved, dirty, saveMeal, editMeal, deleteMeal, undoDelete } = meals
  const goalSettings = useGoalSettings(journal.preferences, ready, commit, setStatus)
  const { preferences, healthCondition } = goalSettings

  return <main id="main" className="site-shell">
    <a className="skip-link" href="#scan">Skip to food upload</a>
    <header className="site-header"><a href="#main" className="brand"><span className="brand-icon"><Utensils size={22} /></span><span>AI Food Recognition<span className="brand-subtitle">Nutrition-aware recommendations</span></span></a><a href="#history" className="text-button">Meal journal <ArrowRight size={15} /></a></header>
    <section className="hero"><p className="eyebrow flex items-center gap-2"><Leaf size={16} /> A little awareness. A better everyday.</p><h1>Know your plate.<br /><span>Nourish your day.</span></h1><p>Turn a food photo into a clearer picture of your meal.<br className="hidden sm:block" /> Review your portions, save your meals, and find your balance.</p>
      <ol className="steps" aria-label="Meal workflow"><li><span>1</span>Scan</li><li><span>2</span>Review portions</li><li><span>3</span>Save meal</li></ol>
    </section>
    {storageError && <p role="alert" className="notice mb-6">{storageError}</p>}
    <div className="dashboard-grid">
      <div className="min-w-0 space-y-7">
        <section id="scan" className="panel" aria-labelledby="scan-heading"><div className="section-heading"><div><p className="eyebrow">01 / Start with a photo</p><h2 id="scan-heading">Let’s see your meal.</h2></div><span className="pill">Food scanner</span></div>
          <ImageUpload onImageSelect={analyzeFood} isAnalyzing={busy} previewUrl={imageUrl} onReset={reset} />
          {error && <div className="notice mt-4"><p role="alert">{error}</p>{file && <button className="btn-secondary mt-3" disabled={busy} onClick={() => void analyzeFood(file)}>Retry analysis</button>}</div>}
          {analysis && !analysis.detections.length && <p className="notice mt-4">Try a clearer photo with good lighting and the food centered.</p>}
          <p role="status" aria-live="polite" className={status ? 'scan-status' : 'sr-only'}>{status}</p>
          <p className="muted text-xs mt-4">Your photo is processed for analysis, never saved in your meal journal.</p>
        </section>
      </div>
      <aside className="dashboard-aside min-w-0 space-y-5" aria-label="Daily summary and settings">
        <DailySummary totals={daily} targetCalories={preferences.calories} mealCount={todaysMeals.length} />
        <GoalSettings settings={goalSettings} />
        <div className="privacy-note"><Leaf size={18} className="shrink-0" /><p>A private little journal.<br /><span>Meals stay on this device. Photos don’t.</span></p></div>
      </aside>
      {analysis && draft && imageUrl && <div className="review-section min-w-0"><ResultsPanel analysis={analysis} draft={draft} imageUrl={imageUrl} onChange={setDraft} onSave={saveMeal} saved={!!saved} dirty={dirty} canSave={ready} userGoal={preferences.goal} healthCondition={healthCondition} /></div>}
    </div>
    <div className="mt-9">
      {deleted && <div className="notice mb-4 flex flex-wrap items-center justify-between gap-3"><span>Meal removed from your journal.</span><button className="btn-secondary" onClick={undoDelete}>Undo delete</button></div>}
      <MealHistory meals={journal.meals} today={today} onEdit={editMeal} onDelete={deleteMeal} onClear={() => {
        if (!commit(previous => ({ ...previous, meals: [] }))) return false
        setDeleted(null); setStatus('Meal history cleared. Goals were kept.'); return true
      }} />
    </div>
    <footer className="site-footer"><span>AI Food Recognition · Final Year Project</span><span>Nutrition estimates, not medical advice.</span></footer>
  </main>
}
