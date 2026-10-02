import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Navigate } from 'react-router-dom'
import { api } from '../api.js'
import Screen, { Button, Input } from '../components/Screen.jsx'
import { useT } from '../i18n/index.jsx'
import { useSpaces } from '../spaces.jsx'

const post = (path, body) => api(path, { method: 'POST', body: JSON.stringify(body ?? {}) })

function CopyUrl({ url }) {
  const { t } = useT()
  return (
    <button type="button" onClick={() => navigator.clipboard.writeText(url)} className="break-all text-xs text-rose-600 underline">
      {url} {t('common.copyHint', { valid: t('common.days7') })}
    </button>
  )
}

function OwnerTools({ space }) {
  const { t, tError } = useT()
  const qc = useQueryClient()
  const [name, setName] = useState(space.name)
  const [person, setPerson] = useState('')
  const [links, setLinks] = useState({})
  const [error, setError] = useState(null)
  const guard = (fn) => async (e) => {
    e?.preventDefault()
    setError(null)
    try { await fn() } catch (err) { setError(tError(err)) }
  }

  const rename = guard(async () => {
    await api(`/spaces/${space.id}`, { method: 'PATCH', body: JSON.stringify({ name }) })
    qc.invalidateQueries({ queryKey: ['spaces'] })
  })
  const inviteNew = guard(async () => {
    setLinks({ ...links, newPerson: (await post(`/spaces/${space.id}/invites`, { display_name: person })).url })
    setPerson('')
  })
  const inviteExisting = guard(async () => setLinks({ ...links, existing: (await post(`/spaces/${space.id}/invites`)).url }))

  return (
    <div className="flex w-full max-w-sm flex-col gap-4">
      <form className="flex justify-center gap-2" onSubmit={rename}>
        <Input value={name} onChange={(e) => setName(e.target.value)} />
        <Button type="submit">{t('space.rename')}</Button>
      </form>
      <form className="flex flex-col items-center gap-2" onSubmit={inviteNew}>
        <Input placeholder={t('space.inviteNewPlaceholder')} value={person} onChange={(e) => setPerson(e.target.value)} />
        <Button type="submit" disabled={!person}>{t('space.inviteNew')}</Button>
        {links.newPerson && <CopyUrl url={links.newPerson} />}
      </form>
      <div className="flex flex-col items-center gap-2">
        <Button onClick={inviteExisting}>{t('space.inviteExisting')}</Button>
        {links.existing && <CopyUrl url={links.existing} />}
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  )
}

export default function Space() {
  const { t } = useT()
  const { active } = useSpaces()
  const members = useQuery({ queryKey: ['members', active?.id], queryFn: () => api(`/spaces/${active.id}/members`), enabled: !!active })
  if (!active) return <Navigate to="/" replace />

  return (
    <Screen title={active.name}>
      <section className="flex w-full max-w-sm flex-col gap-2">
        <h2 className="font-bold">{t('space.members')}</h2>
        {members.data?.map((m) => (
          <div key={m.id} className="flex justify-between rounded-xl bg-white p-3 text-sm shadow-sm">
            <span>{m.display_name}</span><span className="text-rose-400">{t(`space.${m.role}`)}</span>
          </div>
        ))}
      </section>
      {active.role === 'owner' && <OwnerTools key={active.id} space={active} />}
    </Screen>
  )
}
