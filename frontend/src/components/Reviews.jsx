import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../api.js'
import { useMe } from '../auth.js'
import { useT } from '../i18n/index.jsx'
import { Button } from './Screen.jsx'

const AGAIN = ['yes', 'maybe', 'no']

export function Hearts({ value, onChange }) {
  return (
    <span className="text-2xl">
      {[1, 2, 3, 4, 5].map((n) =>
        onChange ? (
          <button key={n} type="button" aria-label={String(n)} onClick={() => onChange(n)} className="active:scale-90">
            {n <= value ? '❤️' : '🤍'}
          </button>
        ) : (
          <span key={n}>{n <= Math.round(value) ? '❤️' : '🤍'}</span>
        ),
      )}
    </span>
  )
}

function MyReview({ date, mine }) {
  const { t, tError } = useT()
  const qc = useQueryClient()
  const [rating, setRating] = useState(mine?.rating ?? 0)
  const [again, setAgain] = useState(mine?.again ?? null)
  const [notes, setNotes] = useState(mine?.notes ?? '')
  const [msg, setMsg] = useState(null)

  async function onSave(e) {
    e.preventDefault()
    try {
      await api(`/dates/${date.id}/review`, { method: 'PUT', body: JSON.stringify({ rating, again, notes: notes || null }) })
      qc.invalidateQueries({ queryKey: ['date', String(date.id)] })
      qc.invalidateQueries({ queryKey: ['dates'] })
      setMsg(t('reviews.saved'))
    } catch (err) {
      setMsg(tError(err))
    }
  }

  return (
    <form onSubmit={onSave} className="flex flex-col gap-2 rounded-2xl bg-white p-4 shadow-sm">
      <h3 className="font-bold">{t('reviews.mine')}</h3>
      <Hearts value={rating} onChange={setRating} />
      <div className="flex gap-2">
        <span className="text-sm">{t('reviews.again')}</span>
        {AGAIN.map((a) => (
          <button key={a} type="button" onClick={() => setAgain(a)}
            className={`rounded-full px-3 py-1 text-sm font-bold ${again === a ? 'bg-rose-500 text-white' : 'bg-rose-100'}`}>
            {t(`reviews.${a}`)}
          </button>
        ))}
      </div>
      <textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder={t('reviews.notes')} rows={3}
        className="rounded-xl border border-rose-200 px-3 py-2 outline-rose-400" />
      <Button type="submit" disabled={!rating || !again}>{t('reviews.save')}</Button>
      {msg && <p className="text-sm">{msg}</p>}
    </form>
  )
}

export default function Reviews({ date }) {
  const { t } = useT()
  const { data: me } = useMe()
  const mine = date.reviews.find((r) => r.user_id === me.id)
  const others = date.reviews.filter((r) => r.user_id !== me.id)

  return (
    <section className="flex flex-col gap-3">
      {others.map((r) => (
        <div key={r.user_id} className="rounded-2xl bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="font-bold">{r.display_name}</span>
            <Hearts value={r.rating} />
          </div>
          <p className="text-sm text-rose-400">{t('reviews.again')} {t(`reviews.${r.again}`)}</p>
          {r.notes && <p className="mt-1 whitespace-pre-line text-sm">{r.notes}</p>}
        </div>
      ))}
      <MyReview key={date.id} date={date} mine={mine} />
    </section>
  )
}
