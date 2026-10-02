import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '../api.js'
import { useT } from '../i18n/index.jsx'
import { useSpaces } from '../spaces.jsx'

// A recipe someone shared with me → an independent copy in one of my spaces.
export default function CopyRecipe({ recipeId }) {
  const { t, tError } = useT()
  const { spaces, active, setActive } = useSpaces()
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [target, setTarget] = useState(active?.id ?? '')
  const [error, setError] = useState(null)
  if (!spaces.length) return null

  async function onCopy() {
    try {
      const { id } = await api(`/recipes/${recipeId}/copy`, { method: 'POST', body: JSON.stringify({ target_space_id: Number(target) }) })
      setActive(Number(target))
      qc.invalidateQueries({ queryKey: ['recipes'] })
      navigate(`/recipes/${id}`)
    } catch (err) {
      setError(tError(err))
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-2xl bg-white p-3 text-sm shadow-sm">
      📋 {t('copy.into')}
      <select value={target} onChange={(e) => setTarget(e.target.value)} className="rounded-xl border border-rose-200 px-2 py-1">
        {spaces.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
      </select>
      <button onClick={onCopy} className="rounded-full bg-rose-500 px-3 py-1 font-bold text-white">{t('copy.button')}</button>
      {error && <p className="w-full text-xs text-red-600">{error}</p>}
    </div>
  )
}
