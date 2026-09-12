import { supportedFoods } from './generated/supportedFoods'

const normalize = (value: string) => value.toLowerCase().replace(/[\s_-]+/g, ' ').trim()

export const alphabeticalFoods = [...supportedFoods].sort((a, b) => a.name.localeCompare(b.name, 'en'))

export function searchSupportedFoods(query: string) {
  const normalized = normalize(query)
  return alphabeticalFoods.filter(food => normalize(food.name).includes(normalized) || normalize(food.id).includes(normalized))
}

const exampleIds = ['idli', 'dosa', 'roti', 'samosa', 'biryani', 'palak_paneer']
export const supportedFoodExamples = exampleIds.map(id => supportedFoods.find(food => food.id === id)).filter(food => food !== undefined)
