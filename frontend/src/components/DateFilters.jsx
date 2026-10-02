import { useState } from 'react'
import { useT } from '../i18n/index.jsx'
import { Hearts } from './Reviews.jsx'
import { TagPicker } from './Tags.jsx'

const field = 'rounded-xl border border-rose-200 bg-white px-3 py-2 text-sm outline-rose-400'

// Filters live in the URL (?tag=1&tag=2&min_rating=4&...), so they survive reloads and can be bookmarked.
export default function DateFilters({ params, setParams }) {
  const { t } = useT()
  const [open, setOpen] = useState(false)
  const set = (key, value) => {
    const next = new URLSearchParams(params)
    next.delete(key)
    ;[].concat(value ?? []).filter((v) => v !== '' && v !== false).forEach((v) => next.append(key, v))
    setParams(next, { replace: true })
  }
  const tags = params.getAll('tag').map(Number)
  const active = [...params.keys()].filter((k) => k !== 'q').length

  return (
    <div className="flex flex-col gap-2">
      <div className="flex gap-2">
        <input type="search" placeholder={t('filters.search')} value={params.get('q') ?? ''} onChange={(e) => set('q', e.target.value)} className={`${field} flex-1`} />
        <button onClick={() => setOpen(!open)} className="rounded-full bg-white px-4 text-sm font-bold shadow-sm">
          {t('filters.title')}{active ? ` (${active})` : ''}
        </button>
      </div>
      {open && (
        <div className="flex flex-col gap-3 rounded-2xl bg-white p-4 text-sm shadow-sm">
          <TagPicker value={tags} onChange={(fn) => set('tag', fn(tags))} allowCreate={false} />
          <div className="flex items-center gap-2">{t('filters.minRating')}
            <Hearts value={Number(params.get('min_rating') ?? 0)} onChange={(n) => set('min_rating', String(n) === params.get('min_rating') ? '' : n)} />
          </div>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={params.get('both_yes') === 'true'} onChange={(e) => set('both_yes', e.target.checked && 'true')} />
            {t('filters.bothYes')}
          </label>
          <label className="flex items-center gap-2">{t('filters.maxCost')}
            <input type="number" min="0" inputMode="decimal" value={params.get('max_cost') ?? ''} onChange={(e) => set('max_cost', e.target.value)} className={`${field} w-24`} />
          </label>
          <div className="flex flex-wrap items-center gap-2">
            {t('filters.from')} <input type="date" value={params.get('from')?.slice(0, 10) ?? ''} onChange={(e) => set('from', e.target.value && `${e.target.value}T00:00:00Z`)} className={field} />
            {t('filters.to')} <input type="date" value={params.get('to')?.slice(0, 10) ?? ''} onChange={(e) => set('to', e.target.value && `${e.target.value}T23:59:59Z`)} className={field} />
          </div>
          <button onClick={() => setParams(new URLSearchParams(), { replace: true })} className="self-start text-rose-500 underline">{t('filters.clear')}</button>
        </div>
      )}
    </div>
  )
}
