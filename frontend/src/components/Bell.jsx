import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '../api.js'
import { formatWhen } from '../dates.js'
import { useT } from '../i18n/index.jsx'

const link = (n) => (n.payload.idea_id ? `/ideas/${n.payload.idea_id}` : n.payload.date_id ? `/dates/${n.payload.date_id}` : '/')

export default function Bell() {
  const { t, locale } = useT()
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const { data } = useQuery({ queryKey: ['notifications'], queryFn: () => api('/notifications'), refetchInterval: 60000 })
  const newest = data?.items[0]?.id
  const seen = useRef(newest)

  // Something new arrived: refresh the views it may affect.
  useEffect(() => {
    if (newest && seen.current && newest !== seen.current) {
      for (const key of ['ideas', 'idea', 'timeline', 'dates', 'date', 'calendar']) qc.invalidateQueries({ queryKey: [key] })
    }
    seen.current = newest
  }, [newest, qc])

  async function markRead(ids) {
    await api('/notifications/read', { method: 'POST', body: JSON.stringify(ids ? { ids } : {}) })
    qc.invalidateQueries({ queryKey: ['notifications'] })
  }

  async function openItem(n) {
    setOpen(false)
    if (!n.read_at) await markRead([n.id])
    navigate(link(n))
  }

  return (
    <div className="relative ml-auto">
      <button onClick={() => setOpen(!open)} aria-label={t('notifications.title')} className="relative text-xl">
        🔔
        {data?.unread > 0 && (
          <span className="absolute -right-2 -top-1 rounded-full bg-rose-600 px-1.5 text-[10px] font-bold text-white">{data.unread}</span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 top-9 z-30 flex max-h-[70vh] w-80 max-w-[90vw] flex-col overflow-y-auto rounded-2xl bg-white p-2 shadow-xl">
          <div className="flex items-center justify-between px-2 py-1">
            <span className="font-bold">{t('notifications.title')}</span>
            {data?.unread > 0 && <button onClick={() => markRead()} className="text-xs text-rose-500 underline">{t('notifications.readAll')}</button>}
          </div>
          {data?.items.length === 0 && <p className="p-3 text-sm">{t('notifications.empty')}</p>}
          {data?.items.map((n) => (
            <button key={n.id} onClick={() => openItem(n)} className={`rounded-xl p-2 text-left text-sm ${n.read_at ? '' : 'bg-rose-50 font-bold'}`}>
              {t(`notifications.kind.${n.kind}`, { actor: n.payload.actor_name ?? '?', title: n.payload.title ?? '' })}
              {n.payload.slots && <span className="block text-xs font-normal text-rose-500">{n.payload.slots.map((s) => formatWhen(locale, s)).join(' · ')}</span>}
              <span className="block text-xs font-normal text-rose-300">{new Date(n.created_at).toLocaleString(locale, { dateStyle: 'short', timeStyle: 'short' })}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
