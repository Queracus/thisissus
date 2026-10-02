import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api.js'
import Photos from '../components/Photos.jsx'
import RecipeCooked from '../components/RecipeCooked.jsx'
import { Hearts } from '../components/Reviews.jsx'
import { TagChips } from '../components/Tags.jsx'
import { useT } from '../i18n/index.jsx'
import { formatAmount, useRecipe } from '../recipes.js'

export default function RecipeDetail() {
  const { id } = useParams()
  const { t, tError, locale } = useT()
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [portions, setPortions] = useState(null)
  const { data: r, error } = useRecipe(id, portions)
  const [added, setAdded] = useState(false)

  async function toShopping() {
    await api('/shopping/from-recipe', { method: 'POST', body: JSON.stringify({ recipe_id: r.id, portions: r.portions }) })
    qc.invalidateQueries({ queryKey: ['shopping'] })
    setAdded(true)
  }

  async function onDelete() {
    if (!confirm(t('recipes.confirmDelete'))) return
    await api(`/recipes/${id}`, { method: 'DELETE' })
    qc.invalidateQueries({ queryKey: ['recipes'] })
    navigate('/recipes', { replace: true })
  }

  return (
    <main className="min-h-[85vh] bg-rose-50 p-4 font-sans text-rose-900">
      {error && <p className="text-center text-sm text-red-600">{tError(error)}</p>}
      {r && (
        <article className="mx-auto flex max-w-md flex-col gap-3">
          <Link to="/recipes" className="text-sm text-rose-500 underline">← {t('recipes.title')}</Link>
          <h1 className="font-display text-3xl italic text-rose-600">{r.title}</h1>
          <p className="text-sm text-rose-400">
            {t(`recipes.status.${r.status}`)} · {t('recipes.portions', { count: r.portions })}{r.prep_minutes != null && ` · ⏱ ${r.prep_minutes} min`}
          </p>
          <TagChips tags={r.tags} />
          {r.avg_rating != null && <p><Hearts value={r.avg_rating} /> <span className="text-sm text-rose-400">{r.avg_rating.toFixed(1)}</span></p>}
          <Photos base={`/recipes/${r.id}`} queryKey={['recipe', String(r.id)]} photos={r.photos} />
          {r.ingredients.length > 0 && (
            <section className="rounded-2xl bg-white p-4 shadow-sm">
              <div className="mb-2 flex items-center justify-between">
                <h2 className="font-bold">{t('recipes.ingredients')}</h2>
                <div className="flex items-center gap-2 text-sm">
                  <button onClick={() => setPortions(Math.max(1, r.portions - 1))} className="h-7 w-7 rounded-full bg-rose-100 font-bold">−</button>
                  <span>{t('recipes.portions', { count: r.portions })}</span>
                  <button onClick={() => setPortions(r.portions + 1)} className="h-7 w-7 rounded-full bg-rose-100 font-bold">+</button>
                </div>
              </div>
              <ul className="flex flex-col gap-1 text-sm">
                {r.ingredients.map((i, n) => (
                  <li key={n}><span className="font-bold">{formatAmount(locale, i.amount)} {i.unit}</span> {i.item}</li>
                ))}
              </ul>
              <button onClick={toShopping} className="mt-3 text-sm font-bold text-rose-600 underline">
                🛒 {t(added ? 'shopping.added' : 'shopping.addRecipe')}
              </button>
            </section>
          )}
          {r.steps.length > 0 && (
            <section className="rounded-2xl bg-white p-4 shadow-sm">
              <h2 className="mb-2 font-bold">{t('recipes.steps')}</h2>
              <ol className="flex list-decimal flex-col gap-2 pl-5 text-sm">{r.steps.map((s, n) => <li key={n} className="whitespace-pre-line">{s}</li>)}</ol>
            </section>
          )}
          <RecipeCooked recipe={r} />
          {r.source_url && <a href={r.source_url} target="_blank" rel="noreferrer noopener" className="break-all text-sm text-rose-600 underline">🔗 {r.source_url}</a>}
          <div className="mt-2 flex gap-4">
            <Link to={`/recipes/${r.id}/edit`} className="text-sm text-rose-500 underline">{t('dates.edit')}</Link>
            <button onClick={onDelete} className="text-sm text-red-600 underline">{t('dates.delete')}</button>
          </div>
        </article>
      )}
    </main>
  )
}
