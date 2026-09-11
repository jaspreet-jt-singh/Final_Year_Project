import { chromium } from '../frontend/node_modules/playwright/index.mjs'

export const launchBrowser = () => chromium.launch({ headless: true, ...(process.env.BROWSER_CHANNEL ? { channel: process.env.BROWSER_CHANNEL } : {}) })
export function mockMacros(input = {}) {
  return { goal: input.goal || 'Maintenance', goal_key: (input.goal || 'Maintenance').toLowerCase().replaceAll(' ', '_'), target_calories: input.target_calories || 2000,
    carbs_g: 250, protein_g: (input.target_calories || 2000) / 10, fat_g: 56, carbs_percent: 50, protein_percent: 25, fat_percent: 25,
    description: 'Test target', health_condition: input.health_condition || 'none', health_condition_key: input.health_condition || 'none' }
}
