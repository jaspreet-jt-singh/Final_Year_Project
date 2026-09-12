// Offline: exercise real frontend functions with an independent BigInt oracle.
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { calculateLocalMacros } from '../frontend/lib/goals.ts'
import { totalNutrition } from '../frontend/lib/meals.ts'

const fields = ['calories', 'protein_g', 'carbs_g', 'fat_g']
function ratio(value) {
  const [mantissa, exponent = '0'] = String(value).toLowerCase().split('e')
  const [integer, decimal = ''] = mantissa.split('.')
  const power = Number(exponent) - decimal.length
  const numerator = BigInt(integer + decimal)
  return power >= 0 ? [numerator * 10n ** BigInt(power), 1n] : [numerator, 10n ** BigInt(-power)]
}
const multiply = ([a, b], [c, d]) => [a * c, b * d]
const add = ([a, b], [c, d]) => [a * d + c * b, b * d]
const divide = ([a, b], [c, d]) => [a * d, b * c]
function even([numerator, denominator]) {
  const quotient = numerator / denominator, remainder = numerator % denominator
  return Number(quotient + (2n * remainder > denominator || (2n * remainder === denominator && quotient % 2n !== 0n) ? 1n : 0n))
}
const approximate = ([a, b]) => Number(a) / Number(b)
function goalOracle(policy, goal, condition, calories) {
  const weights = ['carbs', 'protein', 'fat'].map(key => multiply(ratio(policy.goals[goal][`${key}_percent`]), ratio(policy.modifiers[condition][key])))
  const total = weights.reduce(add, [0n, 1n])
  const percentages = weights.slice(0, 2).map(weight => even(divide(multiply(weight, [100n, 1n]), total)))
  percentages.push(100 - percentages[0] - percentages[1])
  const grams = percentages.map((percent, index) => even([BigInt(calories * percent), BigInt([400, 400, 900][index])]))
  return Object.fromEntries(['carbs_percent', 'protein_percent', 'fat_percent', 'carbs_g', 'protein_g', 'fat_g'].map((key, i) => [key, [...percentages, ...grams][i]]))
}
assert.equal(even([5n, 2n]), 2)
assert.equal(even([7n, 2n]), 4)
assert.equal(approximate(ratio('1.25e-2')), .0125)
assert.equal(approximate(multiply(ratio('12.3'), [25n, 100n])), 3.075)
if (process.argv.includes('--self-test')) {
  console.log(JSON.stringify({ oracle_self_tests: 4, status: 'passed' }))
} else {
  const at = process.argv.indexOf('--input')
  if (at < 0) throw new Error('Use --input PATH or --self-test')
  const { policy, fixtures, foods } = JSON.parse(readFileSync(process.argv[at + 1], 'utf8'))
  const report = { goal_cases: 0, goal_differences: [], fixture_cases: fixtures.length, fixture_differences: [],
    portion_cases: 0, portion_numeric_comparisons: 0, portion_differences: [], max_portion_absolute_error: 0,
    absolute_tolerance: 1e-9, relative_tolerance: 1e-12, invariant_checks: 0 }
  for (const goal of Object.keys(policy.goals)) for (const condition of Object.keys(policy.conditions)) {
    for (let calories = 500; calories <= 5000; calories++) {
      const expected = goalOracle(policy, goal, condition, calories), actual = calculateLocalMacros(goal, calories, condition)
      report.goal_cases++
      if (Object.entries(expected).some(([key, value]) => actual[key] !== value)) report.goal_differences.push({ goal, condition, calories, expected, actual })
    }
  }
  for (const fixture of fixtures) {
    const expected = goalOracle(policy, fixture.goal, fixture.condition, fixture.calories)
    const actual = calculateLocalMacros(fixture.goal, fixture.calories, fixture.condition)
    if (Object.entries(expected).some(([key, value]) => actual[key] !== value || fixture.expected[key] !== value)) report.fixture_differences.push({ goal: fixture.goal, condition: fixture.condition, calories: fixture.calories })
  }
  for (const food of foods) for (let grams = 25; grams <= 1000; grams += 25) {
    const item = { included: true, grams, per100g: food.macros }
    const actual = totalNutrition([item])
    report.portion_cases++
    if (!food.macros) {
      if (!actual.incomplete || actual.knownItems !== 0) report.portion_differences.push({ class: food.class, grams, reason: 'unknown not explicit' })
      continue
    }
    for (const field of fields) {
      const expected = approximate(multiply(ratio(food.macros[field]), [BigInt(grams), 100n]))
      const error = Math.abs(actual[field] - expected)
      report.max_portion_absolute_error = Math.max(report.max_portion_absolute_error, error)
      report.portion_numeric_comparisons++
      if (error > Math.max(report.absolute_tolerance, Math.abs(expected) * report.relative_tolerance)) report.portion_differences.push({ class: food.class, grams, field, expected, actual: actual[field] })
    }
  }
  const known = { included: true, grams: 125, per100g: { calories: 123.45, protein_g: 1.25, carbs_g: 20.5, fat_g: 3.75 } }
  const unknown = { included: true, grams: 100, per100g: null }
  assert.equal(totalNutrition([unknown]).incomplete, true)
  assert.equal(totalNutrition([unknown]).knownItems, 0)
  assert.equal(totalNutrition([known, unknown]).incomplete, true)
  assert.deepEqual(totalNutrition([known, { ...unknown, included: false }]), totalNutrition([known]))
  assert.deepEqual(totalNutrition([{ ...known, included: false }]), totalNutrition([]))
  assert.equal(totalNutrition([known, known]).calories, 2 * totalNutrition([known]).calories)
  const second = { ...known, grams: 250 }
  assert.deepEqual(totalNutrition([known, second]), totalNutrition([second, known]))
  assert.equal(totalNutrition([known]).protein_g, 1.5625)
  report.invariant_checks = 8
  report.goal_difference_count = report.goal_differences.length
  report.fixture_difference_count = report.fixture_differences.length
  report.portion_difference_count = report.portion_differences.length
  console.log(JSON.stringify(report))
}
