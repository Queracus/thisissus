import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'
import { SEASONS, SEASON_EMOJI, useIdeas } from '../ideas.js'
import { useT } from '../i18n/index.jsx'
import { BigButton } from './InviteCard.jsx'
import { TagPicker } from './Tags.jsx'

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

// "Surprise us": filter, then a short shuffle through open ideas before revealing the pick.
export default function SurprisePicker() {
  const { t } = useT()
  const { data: ideas = [] } = useIdeas()
  const [open, setOpen] = useState(false)
  const [tags, setTags] = useState([])
  const [season, setSeason] = useState(null)
  const [maxCost, setMaxCost] = useState('')
  const [shown, setShown] = useState(null)
  const [pick, setPick] = useState(undefined)

  async function spin() {
    const qs = new URLSearchParams()
    tags.forEach((id) => qs.append('tag', id))
    if (season) qs.set('season', season)
    if (maxCost !== '') qs.set('max_cost', maxCost)
    setPick(undefined)
    const result = api(`/ideas/random?${qs}`)
    for (let i = 0; i < 10 && ideas.length; i++) {
      setShown(ideas[i % ideas.length].title)
      await sleep(70 + i * 15)
    }
    const chosen = await result
    setShown(null)
    setPick(chosen)
  }

  if (!open) return <button onClick={() => setOpen(true)} className="self-start rounded-full bg-white px-4 py-2 text-sm font-bold shadow-sm">🎲 {t('surprise.open')}</button>

  return (
    <section className="flex flex-col items-center gap-3 rounded-2xl bg-white p-4 text-sm shadow-sm">
      <TagPicker value={tags} onChange={(fn) => setTags(fn)} allowCreate={false} />
      <div className="flex flex-wrap justify-center gap-2">
        {SEASONS.map((s) => (
          <button key={s} onClick={() => setSeason(season === s ? null : s)} className={`rounded-full px-3 py-1 ${season === s ? 'bg-rose-500 text-white' : 'bg-rose-50'}`}>
            {SEASON_EMOJI[s]} {t(`ideas.season.${s}`)}
          </button>
        ))}
      </div>
      <label className="flex items-center gap-2">{t('filters.maxCost')}
        <input type="number" min="0" inputMode="decimal" value={maxCost} onChange={(e) => setMaxCost(e.target.value)} className="w-24 rounded-xl border border-rose-200 px-3 py-2" />
      </label>
      <BigButton onClick={spin}>🎲 {t('surprise.spin')}</BigButton>
      {shown && <p className="animate-pulse font-display text-2xl italic text-rose-400">{shown}</p>}
      {pick === null && <p>{t('surprise.none')}</p>}
      {pick && (
        <Link to={`/ideas/${pick.id}`} className="animate-pop-in rounded-2xl bg-rose-50 px-6 py-4 text-center">
          <span className="font-display text-3xl italic text-rose-600">{pick.title}</span>
          <span className="block text-xs text-rose-400">{t('surprise.openIdea')}</span>
        </Link>
      )}
      <button onClick={() => setOpen(false)} className="text-xs underline">{t('photos.close')}</button>
    </section>
  )
}
