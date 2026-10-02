import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api.js'
import { FloatingHearts } from '../components/InviteCard.jsx'
import { useT } from '../i18n/index.jsx'
import { SharedBody } from './SharedWithMe.jsx'

const ICON = { date: '💕', idea: '💡', recipe: '🍲' }

// Public page for secret links (/s/:token and /s/:token/:type/:id): no login, read-only, photos via the link.
export default function PublicLink() {
  const { token, type, id } = useParams()
  const { t, locale } = useT()
  const path = type ? `/s/${token}/${type}/${id}` : `/s/${token}`
  const { data, error } = useQuery({ queryKey: ['link', path], queryFn: () => api(path), retry: false })
  const mediaFor = (mediaId, variant) => `/api/s/${token}/media/${mediaId}/${variant}`

  return (
    <main className="relative min-h-screen bg-gradient-to-b from-rose-50 to-pink-100 p-4 font-sans text-rose-900">
      <FloatingHearts count={10} />
      <div className="relative z-10 mx-auto max-w-md animate-pop-in rounded-3xl bg-white/75 p-5 shadow-xl backdrop-blur">
        {error && <p className="py-10 text-center">{t('links.gone')}</p>}
        {data?.type === 'section' && (
          <div className="flex flex-col gap-2">
            <h1 className="font-display text-3xl italic text-rose-600">{t(`shares.section.${data.entity_type}`)}</h1>
            <p className="text-xs text-rose-400">{t('shares.from', { name: data.shared_by_name ?? '?', space: data.space_name })}</p>
            {data.items.map((i) => (
              <Link key={i.id} to={`/s/${token}/${data.entity_type}/${i.id}`} className="rounded-2xl bg-white p-3 shadow-sm">
                {ICON[data.entity_type]} {i.title}
              </Link>
            ))}
          </div>
        )}
        {data && data.type !== 'section' && (
          <>
            {type && <Link to={`/s/${token}`} className="text-sm text-rose-500 underline">←</Link>}
            <SharedBody item={data} mediaFor={mediaFor} />
          </>
        )}
        {data?.expires_at && (
          <p className="mt-4 text-center text-xs text-rose-300">
            {t('links.until', { until: new Date(data.expires_at).toLocaleString(locale, { dateStyle: 'short', timeStyle: 'short' }) })}
          </p>
        )}
      </div>
    </main>
  )
}
