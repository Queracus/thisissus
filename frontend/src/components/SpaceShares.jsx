import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api.js'
import { useT } from '../i18n/index.jsx'
import { useSpaces } from '../spaces.jsx'
import LinkMaker from './LinkMaker.jsx'
import { ShareBadge, useContacts } from './ShareSheet.jsx'

const SECTIONS = ['date', 'idea', 'recipe']

// Space settings: share whole sections with a contact + every active share of the space, revocable.
export default function SpaceShares() {
  const { t, tError } = useT()
  const { active } = useSpaces()
  const qc = useQueryClient()
  const { data: contacts = [] } = useContacts()
  const { data: shares = [] } = useQuery({ queryKey: ['shares', 'space', active?.id], queryFn: () => api('/shares'), enabled: !!active })
  const [section, setSection] = useState('recipe')
  const [target, setTarget] = useState('')
  const [error, setError] = useState(null)
  const refresh = () => qc.invalidateQueries({ queryKey: ['shares'] })

  async function onShare(e) {
    e.preventDefault()
    setError(null)
    try {
      await api('/shares', { method: 'POST', body: JSON.stringify({ scope: 'section', entity_type: section, target_user_id: Number(target) }) })
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
    <section className="flex w-full max-w-sm flex-col gap-2 text-left text-sm">
      <h2 className="font-bold">{t('shares.title')}</h2>
      <form onSubmit={onShare} className="flex flex-wrap items-center gap-2">
        <select value={section} onChange={(e) => setSection(e.target.value)} className="rounded-xl border border-rose-200 bg-white px-2 py-1">
          {SECTIONS.map((s) => <option key={s} value={s}>{t(`shares.section.${s}`)}</option>)}
        </select>
        →
        <select value={target} onChange={(e) => setTarget(e.target.value)} className="rounded-xl border border-rose-200 bg-white px-2 py-1">
          <option value="">{t('shares.pickContact')}</option>
          {contacts.map((c) => <option key={c.id} value={c.id}>{c.display_name}</option>)}
        </select>
        <button type="submit" disabled={!target} className="rounded-full bg-rose-500 px-3 py-1 font-bold text-white disabled:opacity-50">{t('shares.share')}</button>
      </form>
      <LinkMaker key={section} scope="section" entityType={section} />
      {error && <p className="text-xs text-red-600">{error}</p>}
      <div className="flex flex-wrap gap-2">{shares.map((s) => <ShareBadge key={s.id} share={s} onRevoke={revoke} />)}</div>
      {shares.length === 0 && <p className="text-xs text-rose-400">{t('shares.none')}</p>}
    </section>
  )
}
