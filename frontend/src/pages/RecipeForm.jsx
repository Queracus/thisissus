import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api.js'
import { Button } from '../components/Screen.jsx'
import { TagPicker } from '../components/Tags.jsx'
import { useT } from '../i18n/index.jsx'
import { useRecipe } from '../recipes.js'

const field = 'w-full rounded-xl border border-rose-200 bg-white px-3 py-2 outline-rose-400'
const blankIngredient = { amount: '', unit: '', item: '' }

export const recipeToForm = (r) => ({
  title: r?.title ?? '', portions: r?.portions ?? 2, prep_minutes: r?.prep_minutes ?? '', source_url: r?.source_url ?? '',
  status: r?.status ?? 'want', tag_ids: r?.tags.map((t) => t.id) ?? [],
  ingredients: r?.ingredients.length ? r.ingredients.map((i) => ({ amount: i.amount ?? '', unit: i.unit ?? '', item: i.item })) : [blankIngredient],
  steps: r?.steps.length ? r.steps : [''],
})

export const formToRecipe = (v) => ({
  title: v.title, portions: Number(v.portions), prep_minutes: v.prep_minutes === '' ? null : Number(v.prep_minutes),
  source_url: v.source_url || null, status: v.status, tag_ids: v.tag_ids,
  ingredients: v.ingredients.filter((i) => i.item.trim()).map((i) => ({ amount: i.amount === '' ? null : Number(i.amount), unit: i.unit || null, item: i.item.trim() })),
  steps: v.steps.filter((s) => s.trim()),
})

// initial = existing recipe (edit); draft = imported values for a new recipe.
export function RecipeEditor({ initial, draft, onSaved }) {
  const { t, tError } = useT()
  const [v, setV] = useState(recipeToForm(initial ?? draft))
  const [error, setError] = useState(null)
  const set = (k) => (e) => { const val = e.target.value; setV((cur) => ({ ...cur, [k]: val })) }
  const setIng = (i, k) => (e) => { const val = e.target.value; setV((cur) => ({ ...cur, ingredients: cur.ingredients.map((x, j) => (j === i ? { ...x, [k]: val } : x)) })) }
  const setStep = (i) => (e) => { const val = e.target.value; setV((cur) => ({ ...cur, steps: cur.steps.map((x, j) => (j === i ? val : x)) })) }
  const without = (key, i) => setV((cur) => ({ ...cur, [key]: cur[key].filter((_, j) => j !== i) }))

  async function onSave(e) {
    e.preventDefault()
    setError(null)
    try {
      const saved = await api(initial ? `/recipes/${initial.id}` : '/recipes', { method: initial ? 'PUT' : 'POST', body: JSON.stringify(formToRecipe(v)) })
      if (draft?.image_url) await api(`/recipes/${saved.id}/photos/from-url`, { method: 'POST', body: JSON.stringify({ url: draft.image_url }) }).catch(() => {})
      onSaved(saved)
    } catch (err) {
      setError(tError(err))
    }
  }

  return (
    <form onSubmit={onSave} className="flex flex-col gap-3 text-sm">
      <label>{t('recipes.field.title')}<input required className={field} value={v.title} onChange={set('title')} /></label>
      <div className="flex gap-2">
        <label className="flex-1">{t('recipes.field.portions')}<input type="number" min="1" required className={field} value={v.portions} onChange={set('portions')} /></label>
        <label className="flex-1">{t('recipes.field.prep_minutes')}<input type="number" min="0" className={field} value={v.prep_minutes} onChange={set('prep_minutes')} /></label>
      </div>
      <label>{t('recipes.field.source_url')}<input type="url" placeholder="https://" className={field} value={v.source_url} onChange={set('source_url')} /></label>
      <div className="flex gap-2">
        {['want', 'cooked'].map((s) => (
          <button key={s} type="button" onClick={() => setV((cur) => ({ ...cur, status: s }))}
            className={`rounded-full px-3 py-1 ${v.status === s ? 'bg-rose-500 text-white' : 'bg-white'}`}>{t(`recipes.status.${s}`)}</button>
        ))}
      </div>
      <fieldset className="flex flex-col gap-2">
        <legend className="font-bold">{t('recipes.ingredients')}</legend>
        {v.ingredients.map((x, i) => (
          <div key={i} className="flex gap-1">
            <input type="number" min="0" step="any" inputMode="decimal" placeholder={t('recipes.field.amount')} className={`${field} w-20`} value={x.amount} onChange={setIng(i, 'amount')} />
            <input placeholder={t('recipes.field.unit')} className={`${field} w-16`} value={x.unit} onChange={setIng(i, 'unit')} />
            <input placeholder={t('recipes.field.item')} className={`${field} flex-1`} value={x.item} onChange={setIng(i, 'item')} />
            <button type="button" onClick={() => without('ingredients', i)} aria-label="✕">✕</button>
          </div>
        ))}
        <button type="button" className="self-start text-rose-500 underline" onClick={() => setV((cur) => ({ ...cur, ingredients: [...cur.ingredients, blankIngredient] }))}>
          + {t('recipes.addIngredient')}
        </button>
      </fieldset>
      <fieldset className="flex flex-col gap-2">
        <legend className="font-bold">{t('recipes.steps')}</legend>
        {v.steps.map((s, i) => (
          <div key={i} className="flex gap-1">
            <span className="pt-2 font-bold text-rose-400">{i + 1}.</span>
            <textarea rows={2} className={`${field} flex-1`} value={s} onChange={setStep(i)} />
            <button type="button" onClick={() => without('steps', i)} aria-label="✕">✕</button>
          </div>
        ))}
        <button type="button" className="self-start text-rose-500 underline" onClick={() => setV((cur) => ({ ...cur, steps: [...cur.steps, ''] }))}>
          + {t('recipes.addStep')}
        </button>
      </fieldset>
      <div>{t('tags.title')}<TagPicker value={v.tag_ids} onChange={(fn) => setV((cur) => ({ ...cur, tag_ids: typeof fn === 'function' ? fn(cur.tag_ids) : fn }))} /></div>
      <Button type="submit">{t('recipes.save')}</Button>
      {error && <p className="text-red-600">{error}</p>}
    </form>
  )
}

function ImportBox({ onDraft }) {
  const { t, tError } = useT()
  const [url, setUrl] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  async function onImport(e) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const d = await api('/recipes/import', { method: 'POST', body: JSON.stringify({ url }) })
      onDraft({ ...d, tags: [], ingredients: d.ingredients, steps: d.steps })
    } catch (err) {
      setError(tError(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={onImport} className="mb-4 flex flex-col gap-2 rounded-2xl bg-white p-3 text-sm shadow-sm">
      <span className="font-bold">🔗 {t('recipes.importTitle')}</span>
      <div className="flex gap-2">
        <input type="url" required placeholder="https://" value={url} onChange={(e) => setUrl(e.target.value)} className={`${field} flex-1`} />
        <button type="submit" disabled={busy} className="rounded-full bg-rose-500 px-4 font-bold text-white disabled:opacity-50">{busy ? '…' : t('recipes.import')}</button>
      </div>
      {error && <p className="text-red-600">{error}</p>}
    </form>
  )
}

export default function RecipeForm() {
  const { id } = useParams()
  const { t } = useT()
  const qc = useQueryClient()
  const navigate = useNavigate()
  const { data } = useRecipe(id)
  const [draft, setDraft] = useState(null)
  const onSaved = (saved) => {
    qc.invalidateQueries({ queryKey: ['recipes'] })
    qc.setQueryData(['recipe', String(saved.id)], saved)
    navigate(`/recipes/${saved.id}`, { replace: true })
  }

  return (
    <main className="min-h-[85vh] bg-rose-50 p-4 font-sans text-rose-900">
      <div className="mx-auto max-w-md">
        <h1 className="mb-3 font-display text-3xl italic text-rose-600">{t(id ? 'recipes.edit' : 'recipes.new')}</h1>
        {id ? data && <RecipeEditor initial={data} onSaved={onSaved} /> : (
          <>
            <ImportBox onDraft={setDraft} />
            <RecipeEditor key={draft?.source_url ?? 'blank'} draft={draft} onSaved={onSaved} />
          </>
        )}
      </div>
    </main>
  )
}
