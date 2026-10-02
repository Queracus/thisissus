import { describe, expect, it } from 'vitest'
import { formToRecipe, recipeToForm } from './RecipeForm.jsx'

describe('recipe form mapping', () => {
  it('drops empty rows and turns blanks into nulls', () => {
    const body = formToRecipe({
      ...recipeToForm(null), title: 'Ramen', prep_minutes: '',
      ingredients: [{ amount: '200', unit: 'g', item: ' noodles ' }, { amount: '', unit: '', item: 'salt' }, { amount: '', unit: '', item: '  ' }],
      steps: ['Boil', '  ', 'Eat'],
    })
    expect(body.ingredients).toEqual([{ amount: 200, unit: 'g', item: 'noodles' }, { amount: null, unit: null, item: 'salt' }])
    expect(body.steps).toEqual(['Boil', 'Eat'])
    expect(body.prep_minutes).toBeNull()
  })

  it('round-trips an existing recipe', () => {
    const recipe = { title: 'X', portions: 4, prep_minutes: 10, source_url: null, status: 'cooked', tags: [{ id: 3 }],
      ingredients: [{ amount: 1.5, unit: 'kg', item: 'rice' }], steps: ['Cook'] }
    expect(formToRecipe(recipeToForm(recipe))).toEqual({ title: 'X', portions: 4, prep_minutes: 10, source_url: null, status: 'cooked',
      tag_ids: [3], ingredients: [{ amount: 1.5, unit: 'kg', item: 'rice' }], steps: ['Cook'] })
  })
})
