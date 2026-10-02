import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api.js'
import { useT } from '../i18n/index.jsx'

export const useContacts = () => useQuery({ queryKey: ['contacts'], queryFn: () => api('/shares/contacts') })

export function ShareBadge({ share, onRevoke }) {
  const { t } = useT()
  const who = share.is_link ? t('shares.link') : share.target_name
  const what = share.scope === 'section' ? t(`shares.section.${share.entity_type}`) : null
  return (
    <span className="flex items-center gap-1 rounded-full bg-rose-100 px-3 py-1 text-xs">
      👁 {what ? `${what} · ` : ''}{t('shares.sharedWith', { who, by: share.created_by_name ?? '?' })}
      {onRevoke && <button onClick={() => onRevoke(share)} aria-label={t('shares.revoke')} className="ml-1 font-bold text-rose-600">✕</button>}
    </span>
  )
}

// Who can see this item + share it with one of my contacts (read-only).
export default function ShareSheet({ entityType, entityId }) {
  const { t, tError } = useT()
  const qc = useQueryClient()
  const key = ['shares', entityType, entityId]
  const { data: shares = [] } = useQuery({ queryKey: key, queryFn: () => api(`/shares?entity_type=${entityType}&entity_id=${entityId}`) })
  const { data: contacts = [] } = useContacts()
  const [open, setOpen] = useState(false)
  const [error, setError] = useState(null)
  const refresh = () => qc.invalidateQueries({ queryKey: ['shares'] })

  async function shareWith(userId) {
    setError(null)
    try {
      await api('/shares', { method: 'POST', body: JSON.stringify({ scope: 'item', entity_type: entityType, entity_id: entityId, target_user_id: userId }) })
      setOpen(false)
      refresh()
    } catch (err) {
      setError(tError(err))
    }
  }

  async function revoke(share) {
    if (!confirm(t('shares.confirmRevoke'))) return
    await api(`/shares/${share.id}`, { method: 'DELETE' })
    refresh()
  }

  return (
    <section className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        {shares.map((s) => <ShareBadge key={s.id} share={s} onRevoke={revoke} />)}
        <button onClick={() => setOpen(!open)} className="rounded-full bg-white px-3 py-1 text-xs font-bold shadow-sm">↗ {t('shares.share')}</button>
      </div>
      {open && (
        <div className="flex flex-wrap gap-2 rounded-2xl bg-white p-3 text-sm shadow-sm">
          <span className="w-full text-xs text-rose-400">{t('shares.pickContact')}</span>
          {contacts.map((c) => (
            <button key={c.id} onClick={() => shareWith(c.id)} className="rounded-full bg-rose-50 px-3 py-1">{c.display_name}</button>
          ))}
          {contacts.length === 0 && <span className="text-xs">{t('shares.noContacts')}</span>}
        </div>
      )}
      {error && <p className="text-xs text-red-600">{error}</p>}
    </section>
  )
}
