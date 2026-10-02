import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api.js'
import LeafletMap from '../components/LeafletMap.jsx'
import { mediaUrl } from '../components/Photos.jsx'
import { formatWhen } from '../dates.js'
import { useT } from '../i18n/index.jsx'
import { useSpaces } from '../spaces.jsx'

const esc = (s) => s.replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`)

export default function MapPage() {
  const { t, locale } = useT()
  const { active } = useSpaces()
  const { data: points = [] } = useQuery({ queryKey: ['map', active?.id], queryFn: () => api('/dates/map'), enabled: !!active })

  const markers = useMemo(() => points.map((p) => ({
    ...p,
    popup: `<a href="/dates/${p.id}" style="display:block;width:160px">
      ${p.thumb_id ? `<img src="${mediaUrl(p.thumb_id, 'thumb')}" style="width:160px;border-radius:8px">` : ''}
      <b>${esc(p.title)}</b><br>${esc(formatWhen(locale, p.starts_at))}</a>`,
  })), [points, locale])

  return (
    <main className="min-h-[85vh] bg-rose-50 p-4 font-sans text-rose-900">
      <div className="mx-auto flex max-w-2xl flex-col gap-3">
        <h1 className="font-display text-3xl italic text-rose-600">{t('map.title')}</h1>
        <LeafletMap markers={markers} className="h-[70vh]" />
        {points.length === 0 && <p className="text-center text-sm">{t('map.empty')}</p>}
      </div>
    </main>
  )
}
