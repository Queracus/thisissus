import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api.js'
import { LinkButton } from './Screen.jsx'

// Active sessions with revoke, for logging out a lost phone.
export default function Devices() {
  const qc = useQueryClient()
  const { data: sessions = [] } = useQuery({ queryKey: ['sessions'], queryFn: () => api('/me/sessions') })
  const run = async (method, path) => {
    await api(path, { method })
    qc.invalidateQueries({ queryKey: ['sessions'] })
  }

  return (
    <section className="flex w-full max-w-sm flex-col gap-2">
      <h2 className="font-bold">Naprave</h2>
      {sessions.map((s) => (
        <div key={s.id} className="flex items-center justify-between gap-2 rounded-xl bg-white p-3 text-left text-xs shadow-sm">
          <span className="truncate">{s.user_agent || 'Neznana naprava'}<br />
            <span className="text-rose-400">{new Date(s.last_seen_at).toLocaleString()}</span></span>
          {s.current ? <span className="font-bold text-rose-500">ta naprava</span>
            : <LinkButton onClick={() => run('DELETE', `/me/sessions/${s.id}`)}>Odjavi</LinkButton>}
        </div>
      ))}
      {sessions.length > 1 && <LinkButton onClick={() => run('POST', '/me/sessions/revoke-others')}>Odjavi vse ostale</LinkButton>}
    </section>
  )
}
