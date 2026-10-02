import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api.js'
import { useT } from '../i18n/index.jsx'
import { LinkButton } from './Screen.jsx'

// Active sessions with revoke, for logging out a lost phone.
export default function Devices() {
  const { t, locale } = useT()
  const qc = useQueryClient()
  const { data: sessions = [] } = useQuery({ queryKey: ['sessions'], queryFn: () => api('/me/sessions') })
  const run = async (method, path) => {
    await api(path, { method })
    qc.invalidateQueries({ queryKey: ['sessions'] })
  }

  return (
    <section className="flex w-full max-w-sm flex-col gap-2">
      <h2 className="font-bold">{t('devices.title')}</h2>
      {sessions.map((s) => (
        <div key={s.id} className="flex items-center justify-between gap-2 rounded-xl bg-white p-3 text-left text-xs shadow-sm">
          <span className="truncate">{s.user_agent || t('devices.unknown')}<br />
            <span className="text-rose-400">{new Date(s.last_seen_at).toLocaleString(locale)}</span></span>
          {s.current ? <span className="font-bold text-rose-500">{t('devices.current')}</span>
            : <LinkButton onClick={() => run('DELETE', `/me/sessions/${s.id}`)}>{t('devices.revoke')}</LinkButton>}
        </div>
      ))}
      {sessions.length > 1 && <LinkButton onClick={() => run('POST', '/me/sessions/revoke-others')}>{t('devices.revokeOthers')}</LinkButton>}
    </section>
  )
}
