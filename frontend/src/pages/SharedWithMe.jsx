import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api.js'
import { mediaUrl } from '../components/Photos.jsx'
import { Hearts } from '../components/Reviews.jsx'
import { TagChips } from '../components/Tags.jsx'
import { formatCost, formatWhen } from '../dates.js'
import { useT } from '../i18n/index.jsx'
import { formatAmount } from '../recipes.js'

const ICON = { date: '💕', idea: '💡', recipe: '🍲' }

export default function SharedWithMe() {
  const { t } = useT()
  const { data: items = [], isLoading } = useQuery({ queryKey: ['shared-with-me'], queryFn: () => api('/shared-with-me') })

  return (
    <main className="min-h-[85vh] bg-rose-50 p-4 font-sans text-rose-900">
      <div className="mx-auto flex max-w-md flex-col gap-2">
        <h1 className="font-display text-3xl italic text-rose-600">{t('shares.withMe')}</h1>
        {!isLoading && items.length === 0 && <p className="py-10 text-center text-sm">{t('shares.nothingYet')}</p>}
        {items.map((i) => (
          <Link key={`${i.type}-${i.id}`} to={`/shared/${i.type}/${i.id}`} className="rounded-2xl bg-white p-3 shadow-sm">
            <span className="font-bold">{ICON[i.type]} {i.title}</span>
            <span className="block text-xs text-rose-400">{t('shares.from', { name: i.shared_by_name ?? '?', space: i.space_name })}</span>
          </Link>
        ))}
      </div>
    </main>
  )
}

// Read-only gallery: thumbnails open the display version (shares never get originals).
export function ReadOnlyPhotos({ photos, mediaFor = mediaUrl }) {
  if (!photos?.length) return null
  return (
    <div className="grid grid-cols-3 gap-1">
      {photos.filter((p) => p.status === 'ready').map((p) => (
        <a key={p.id} href={mediaFor(p.id, p.kind === 'video' ? 'mp4' : 'display')} target="_blank" rel="noreferrer" className="aspect-square overflow-hidden rounded-lg bg-rose-100">
          <img src={mediaFor(p.id, 'thumb')} alt={p.caption ?? ''} loading="lazy" className="h-full w-full object-cover" />
        </a>
      ))}
    </div>
  )
}

export function SharedBody({ item, mediaFor }) {
  const { t, locale } = useT()
  return (
    <article className="mx-auto flex max-w-md flex-col gap-3">
      <h1 className="font-display text-3xl italic text-rose-600">{ICON[item.type]} {item.title}</h1>
      {item.shared_by_name && <p className="text-xs text-rose-400">{t('shares.sharedBy', { name: item.shared_by_name })}</p>}
      {item.starts_at && <p className="text-sm text-rose-400">{formatWhen(locale, item.starts_at, item.ends_at)}</p>}
      {item.scheduled_at && <p className="text-sm text-rose-400">💕 {formatWhen(locale, item.scheduled_at)}</p>}
      {item.place_name && <p>📍 {item.place_name}</p>}
      <TagChips tags={item.tags ?? []} />
      {item.avg_rating != null && <Hearts value={item.avg_rating} />}
      {item.description && <p className="whitespace-pre-line">{item.description}</p>}
      {item.est_cost != null && <p>💶 ~{formatCost(locale, item.est_cost)}</p>}
      <ReadOnlyPhotos photos={item.photos} mediaFor={mediaFor} />
      {item.ingredients?.length > 0 && (
        <section className="rounded-2xl bg-white p-4 shadow-sm">
          <h2 className="mb-2 font-bold">{t('recipes.ingredients')} · {t('recipes.portions', { count: item.portions })}</h2>
          <ul className="text-sm">{item.ingredients.map((i, n) => <li key={n}><b>{formatAmount(locale, i.amount)} {i.unit}</b> {i.item}</li>)}</ul>
        </section>
      )}
      {item.steps?.length > 0 && (
        <section className="rounded-2xl bg-white p-4 shadow-sm">
          <h2 className="mb-2 font-bold">{t('recipes.steps')}</h2>
          <ol className="list-decimal pl-5 text-sm">{item.steps.map((s, n) => <li key={n}>{s}</li>)}</ol>
        </section>
      )}
      {(item.url || item.source_url) && <a href={item.url || item.source_url} target="_blank" rel="noreferrer noopener" className="break-all text-sm text-rose-600 underline">🔗 {item.url || item.source_url}</a>}
    </article>
  )
}

export function SharedItem() {
  const { type, id } = useParams()
  const { tError } = useT()
  const { data, error } = useQuery({ queryKey: ['shared', type, id], queryFn: () => api(`/shared/${type}/${id}`) })
  return (
    <main className="min-h-[85vh] bg-rose-50 p-4 font-sans text-rose-900">
      {error && <p className="text-center text-sm text-red-600">{tError(error)}</p>}
      {data && <SharedBody item={data} />}
    </main>
  )
}
