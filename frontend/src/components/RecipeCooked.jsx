import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '../api.js'
import { useMe } from '../auth.js'
import { useT } from '../i18n/index.jsx'
import { BigButton } from './InviteCard.jsx'
import { Hearts } from './Reviews.jsx'
import { Button } from './Screen.jsx'

function MyRecipeReview({ recipe, mine }) {
  const { t, tError } = useT()
  const qc = useQueryClient()
  const [rating, setRating] = useState(mine?.rating ?? 0)
  const [comment, setComment] = useState(mine?.comment ?? '')
  const [msg, setMsg] = useState(null)

  async function onSave(e) {
    e.preventDefault()
    try {
      await api(`/recipes/${recipe.id}/review`, { method: 'PUT', body: JSON.stringify({ rating, comment: comment || null }) })
      qc.invalidateQueries({ queryKey: ['recipe', String(recipe.id)] })
      qc.invalidateQueries({ queryKey: ['recipes'] })
      setMsg(t('reviews.saved'))
    } catch (err) {
      setMsg(tError(err))
    }
  }

  return (
    <form onSubmit={onSave} className="flex flex-col gap-2 rounded-2xl bg-white p-4 shadow-sm">
      <h3 className="font-bold">{t('reviews.mine')}</h3>
      <Hearts value={rating} onChange={setRating} />
      <textarea rows={2} value={comment} onChange={(e) => setComment(e.target.value)} placeholder={t('recipes.commentPlaceholder')}
        className="rounded-xl border border-rose-200 px-3 py-2 outline-rose-400" />
      <Button type="submit" disabled={!rating}>{t('reviews.save')}</Button>
      {msg && <p className="text-sm">{msg}</p>}
    </form>
  )
}

export default function RecipeCooked({ recipe }) {
  const { t, tError, locale } = useT()
  const { data: me } = useMe()
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [asDate, setAsDate] = useState(false)
  const [error, setError] = useState(null)
  const mine = recipe.reviews.find((r) => r.user_id === me.id)

  async function onCooked() {
    try {
      const { date_id } = await api(`/recipes/${recipe.id}/cooked`, { method: 'POST', body: JSON.stringify({ log_as_date: asDate }) })
      for (const key of ['recipe', 'recipes', 'dates']) qc.invalidateQueries({ queryKey: [key] })
      if (date_id) navigate(`/dates/${date_id}/edit`)
    } catch (err) {
      setError(tError(err))
    }
  }

  return (
    <section className="flex flex-col gap-3">
      <div className="flex flex-col items-center gap-2 rounded-2xl bg-gradient-to-br from-rose-100 to-pink-50 p-4">
        <BigButton onClick={onCooked}>{t('recipes.cooked')} 🍲</BigButton>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={asDate} onChange={(e) => setAsDate(e.target.checked)} /> {t('recipes.logAsDate')}</label>
        {error && <p className="text-sm text-red-600">{error}</p>}
        {recipe.cooks.length > 0 && (
          <p className="text-xs text-rose-400">
            {t('recipes.cookedCount', { count: recipe.cooks.length })} · {t('recipes.lastCooked', { when: new Date(recipe.cooks[0].created_at).toLocaleDateString(locale) })}
          </p>
        )}
      </div>
      {recipe.reviews.filter((r) => r.user_id !== me.id).map((r) => (
        <div key={r.user_id} className="rounded-2xl bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between"><span className="font-bold">{r.display_name}</span><Hearts value={r.rating} /></div>
          {r.comment && <p className="mt-1 whitespace-pre-line text-sm">{r.comment}</p>}
        </div>
      ))}
      <MyRecipeReview key={recipe.id} recipe={recipe} mine={mine} />
    </section>
  )
}
