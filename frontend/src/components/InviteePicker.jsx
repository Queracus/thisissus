import { useQuery } from '@tanstack/react-query'
import { api } from '../api.js'
import { useMe } from '../auth.js'
import { useT } from '../i18n/index.jsx'
import { useSpaces } from '../spaces.jsx'

// value: null = everyone in the space, or a list of user ids. Hidden for couples (nothing to choose).
export default function InviteePicker({ value, onChange }) {
  const { t } = useT()
  const { data: me } = useMe()
  const { active } = useSpaces()
  const { data: members = [] } = useQuery({ queryKey: ['members', active?.id], queryFn: () => api(`/spaces/${active.id}/members`), enabled: !!active })
  const others = members.filter((m) => m.id !== me.id)
  if (others.length < 2) return null

  const toggle = (id) => onChange((cur) => {
    const base = cur.invitee_ids ?? others.map((m) => m.id)
    const next = base.includes(id) ? base.filter((x) => x !== id) : [...base, id]
    return { ...cur, invitee_ids: next.length === others.length ? null : next }
  })

  return (
    <div className="flex flex-col gap-1">
      {t('invitees.title')}
      <div className="flex flex-wrap gap-2">
        {others.map((m) => {
          const on = value === null || value.includes(m.id)
          return (
            <button key={m.id} type="button" onClick={() => toggle(m.id)} className={`rounded-full px-3 py-1 ${on ? 'bg-rose-500 text-white' : 'bg-white'}`}>
              {m.display_name}
            </button>
          )
        })}
      </div>
      <span className="text-xs text-rose-400">{t(value === null ? 'invitees.everyone' : 'invitees.some')}</span>
    </div>
  )
}
