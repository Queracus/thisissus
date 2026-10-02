import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api.js'
import { useMe } from '../auth.js'
import { formatWhen, fromLocalInput } from '../dates.js'
import { useT } from '../i18n/index.jsx'
import { Button } from './Screen.jsx'

const field = 'rounded-xl border border-rose-200 bg-white px-3 py-2 text-sm outline-rose-400'
const pill = 'rounded-full px-4 py-2 text-sm font-bold shadow-sm active:scale-95'

function SlotsEditor({ onSubmit, onCancel, submitLabel }) {
  const { t } = useT()
  const [slots, setSlots] = useState([''])
  const set = (i, v) => setSlots((cur) => cur.map((s, j) => (j === i ? v : s)))

  return (
    <form className="flex flex-col gap-2" onSubmit={(e) => { e.preventDefault(); onSubmit(slots.filter(Boolean).map(fromLocalInput)) }}>
      {slots.map((s, i) => (
        <div key={i} className="flex gap-2">
          <input type="datetime-local" required value={s} onChange={(e) => set(i, e.target.value)} className={`${field} flex-1`} />
          {slots.length > 1 && <button type="button" onClick={() => setSlots((cur) => cur.filter((_, j) => j !== i))}>✕</button>}
        </div>
      ))}
      {slots.length < 3 && <button type="button" className="self-start text-sm text-rose-500 underline" onClick={() => setSlots((cur) => [...cur, ''])}>+ {t('proposals.addSlot')}</button>}
      <div className="flex gap-2">
        <Button type="submit">{submitLabel}</Button>
        {onCancel && <button type="button" onClick={onCancel} className="text-sm underline">{t('common.back')}</button>}
      </div>
    </form>
  )
}

function Timeline({ events }) {
  const { t, locale } = useT()
  const when = (iso) => new Date(iso).toLocaleString(locale, { dateStyle: 'short', timeStyle: 'short' })
  const detail = (e) => {
    if (e.kind === 'comment') return `“${e.payload.text}”`
    if (e.payload.slots) return e.payload.slots.map((s) => formatWhen(locale, s)).join(' · ')
    if (e.payload.slot) return formatWhen(locale, e.payload.slot)
    return ''
  }
  return (
    <ol className="flex flex-col gap-2 border-l-2 border-rose-200 pl-3 text-sm">
      {events.map((e) => (
        <li key={e.id}>
          <span className="font-bold">{e.actor_name}</span> {t(`proposals.event.${e.kind}`)} <span className="text-rose-500">{detail(e)}</span>
          <div className="text-xs text-rose-300">{when(e.created_at)}</div>
        </li>
      ))}
    </ol>
  )
}

export default function Negotiation({ idea }) {
  const { t, tError, locale } = useT()
  const { data: me } = useMe()
  const qc = useQueryClient()
  const { data } = useQuery({ queryKey: ['timeline', String(idea.id)], queryFn: () => api(`/ideas/${idea.id}/timeline`) })
  const [mode, setMode] = useState(null) // 'slots' when proposing/countering
  const [comment, setComment] = useState('')
  const [error, setError] = useState(null)

  async function act(action, body) {
    setError(null)
    try {
      const updated = await api(`/ideas/${idea.id}/${action}`, { method: 'POST', body: JSON.stringify(body ?? {}) })
      if (action !== 'comments') qc.setQueryData(['idea', String(idea.id)], updated)
      qc.invalidateQueries({ queryKey: ['timeline', String(idea.id)] })
      qc.invalidateQueries({ queryKey: ['ideas'] })
      setMode(null)
    } catch (err) {
      setError(tError(err))
    }
  }

  const p = data?.proposal
  const mine = p?.proposed_by === me.id
  const slotsAction = idea.status === 'idea' ? 'propose' : 'counter'

  return (
    <section className="flex flex-col gap-3 rounded-2xl bg-white p-4 shadow-sm">
      {mode === 'slots' ? (
        <SlotsEditor submitLabel={t(`proposals.${slotsAction}`)} onCancel={() => setMode(null)} onSubmit={(slots) => act(slotsAction, { slots })} />
      ) : idea.status === 'archived' ? null : idea.status === 'idea' ? (
        <Button onClick={() => setMode('slots')}>📅 {t('proposals.propose')}</Button>
      ) : idea.status === 'scheduled' ? (
        <>
          <p className="font-bold text-rose-600">💕 {t('proposals.scheduledFor', { when: formatWhen(locale, idea.scheduled_at) })}</p>
          <button onClick={() => setMode('slots')} className="self-start text-sm underline">{t('proposals.reschedule')}</button>
        </>
      ) : p && p.awaiting_me ? (
        <>
          <p>{t('proposals.askedBy', { name: p.proposed_by_name })}</p>
          {p.slots.map((s) => (
            <button key={s} onClick={() => act('accept', { slot: s })} className={`${pill} bg-gradient-to-br from-rose-600 to-pink-400 text-white`}>
              ✓ {formatWhen(locale, s)}
            </button>
          ))}
          <div className="flex flex-wrap gap-3 text-sm">
            <button onClick={() => setMode('slots')} className="underline">{t('proposals.counter')}</button>
            <button onClick={() => act('refuse')} className="text-red-600 underline">{t('proposals.refuse')}</button>
          </div>
        </>
      ) : p ? (
        <>
          <p>{t('proposals.waiting')}: {p.slots.map((s) => formatWhen(locale, s)).join(' · ')}</p>
          {p.pending_names.length > 0 && <p className="text-sm text-rose-400">{t('proposals.waitingFor', { names: p.pending_names.join(', ') })}</p>}
          <div className="flex gap-3 text-sm">
            <button onClick={() => setMode('slots')} className="underline">{t('proposals.change')}</button>
            {mine && <button onClick={() => act('cancel')} className="text-red-600 underline">{t('proposals.cancel')}</button>}
          </div>
        </>
      ) : null}
      {idea.status === 'archived'
        ? <button onClick={() => act('reopen')} className="self-start text-sm font-bold text-rose-600 underline">{t('proposals.reopen')}</button>
        : <button onClick={() => confirm(t('proposals.confirmNotForMe')) && act('not-for-me')} className="self-start text-xs text-rose-400 underline">{t('proposals.notForMe')}</button>}
      {error && <p className="text-sm text-red-600">{error}</p>}
      {data?.events.length > 0 && <Timeline events={data.events} />}
      <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); if (comment.trim()) act('comments', { text: comment }).then(() => setComment('')) }}>
        <input value={comment} onChange={(e) => setComment(e.target.value)} placeholder={t('proposals.commentPlaceholder')} className={`${field} flex-1`} />
        <button type="submit" className="text-sm font-bold text-rose-600">{t('proposals.send')}</button>
      </form>
    </section>
  )
}
