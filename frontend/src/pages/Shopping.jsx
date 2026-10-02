import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../api.js'
import { useT } from '../i18n/index.jsx'
import { formatAmount } from '../recipes.js'
import { useSpaces } from '../spaces.jsx'

export default function Shopping() {
  const { t, locale } = useT()
  const { active } = useSpaces()
  const qc = useQueryClient()
  const key = ['shopping', active?.id]
  const { data: items = [] } = useQuery({ queryKey: key, queryFn: () => api('/shopping'), enabled: !!active, refetchInterval: 15000 })
  const [draft, setDraft] = useState('')
  const send = async (method, path, body) => {
    await api(path, { method, body: JSON.stringify(body ?? {}) })
    qc.invalidateQueries({ queryKey: ['shopping'] })
  }

  async function onAdd(e) {
    e.preventDefault()
    if (!draft.trim()) return
    await send('POST', '/shopping', { item: draft.trim() })
    setDraft('')
  }

  return (
    <main className="min-h-[85vh] bg-rose-50 p-4 font-sans text-rose-900">
      <div className="mx-auto flex max-w-md flex-col gap-3">
        <h1 className="font-display text-3xl italic text-rose-600">{t('shopping.title')}</h1>
        <form onSubmit={onAdd} className="flex gap-2">
          <input value={draft} onChange={(e) => setDraft(e.target.value)} placeholder={t('shopping.addPlaceholder')}
            className="flex-1 rounded-xl border border-rose-200 bg-white px-3 py-2 outline-rose-400" />
          <button type="submit" className="rounded-full bg-rose-500 px-4 font-bold text-white">+</button>
        </form>
        {items.length === 0 && <p className="py-10 text-center text-sm">{t('shopping.empty')}</p>}
        <ul className="flex flex-col gap-1">
          {items.map((i) => (
            <li key={i.id} className={`flex items-center gap-3 rounded-xl bg-white px-3 py-2 shadow-sm ${i.checked ? 'opacity-50' : ''}`}>
              <input type="checkbox" checked={i.checked} onChange={() => send('PATCH', `/shopping/${i.id}`, { checked: !i.checked })} className="h-5 w-5 accent-rose-500" />
              <span className={`flex-1 ${i.checked ? 'line-through' : ''}`}>
                {i.amount != null && <span className="font-bold">{formatAmount(locale, i.amount)} {i.unit} </span>}{i.item}
              </span>
              {i.recipe_id && <Link to={`/recipes/${i.recipe_id}`} className="text-xs">🍲</Link>}
              <button onClick={() => send('DELETE', `/shopping/${i.id}`)} aria-label="✕" className="text-rose-300">✕</button>
            </li>
          ))}
        </ul>
        {items.some((i) => i.checked) && (
          <button onClick={() => send('POST', '/shopping/clear-checked')} className="self-start text-sm text-rose-500 underline">{t('shopping.clearChecked')}</button>
        )}
      </div>
    </main>
  )
}
