import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, Navigate } from 'react-router-dom'
import { api } from '../api.js'
import { useMe } from '../auth.js'
import { Button, Input } from '../components/Screen.jsx'
import BackupCard from '../components/BackupCard.jsx'
import ExportCard from '../components/ExportCard.jsx'
import { useT } from '../i18n/index.jsx'

const send = (method, path, body) => api(path, { method, body: JSON.stringify(body ?? {}) })

function CopyLink({ url, valid }) {
  const { t } = useT()
  return (
    <button type="button" onClick={() => navigator.clipboard.writeText(url)} className="mt-2 max-w-xs break-all text-left text-xs text-rose-600 underline">
      {url} {t('common.copyHint', { valid })}
    </button>
  )
}

function SpacesAdmin({ users }) {
  const { t } = useT()
  const qc = useQueryClient()
  const spaces = useQuery({ queryKey: ['admin', 'spaces'], queryFn: () => api('/admin/spaces') })
  const [name, setName] = useState('')
  const [ownerId, setOwnerId] = useState('')

  async function onCreate(e) {
    e.preventDefault()
    await send('POST', '/admin/spaces', { name, owner_id: Number(ownerId) })
    setName('')
    qc.invalidateQueries({ queryKey: ['admin', 'spaces'] })
    qc.invalidateQueries({ queryKey: ['spaces'] })
  }

  return (
    <section className="flex flex-col gap-2">
      <h2 className="font-bold">{t('adminSpaces.title')}</h2>
      <form onSubmit={onCreate} className="flex flex-col items-center gap-2">
        <Input placeholder={t('adminSpaces.name')} value={name} onChange={(e) => setName(e.target.value)} />
        <select value={ownerId} onChange={(e) => setOwnerId(e.target.value)} className="w-64 rounded-xl border border-rose-200 bg-white px-4 py-3">
          <option value="">{t('adminSpaces.owner')}</option>
          {users?.map((u) => <option key={u.id} value={u.id}>{u.display_name}</option>)}
        </select>
        <Button type="submit" disabled={!name || !ownerId}>{t('adminSpaces.create')}</Button>
      </form>
      {spaces.data?.map((s) => (
        <div key={s.id} className="rounded-xl bg-white p-3 text-sm shadow-sm">
          <span className="font-bold">{s.name}</span> <span className="text-rose-400">· {s.members.join(', ')}</span>
        </div>
      ))}
    </section>
  )
}

function InviteForm() {
  const { t } = useT()
  const [name, setName] = useState('')
  const [url, setUrl] = useState(null)
  const qc = useQueryClient()

  async function onInvite(e) {
    e.preventDefault()
    setUrl((await send('POST', '/admin/invites', { display_name: name })).url)
    setName('')
    qc.invalidateQueries({ queryKey: ['admin', 'users'] })
  }

  return (
    <form onSubmit={onInvite} className="flex flex-col items-center gap-2">
      <Input placeholder={t('admin.newUserName')} value={name} onChange={(e) => setName(e.target.value)} />
      <Button type="submit" disabled={!name}>{t('admin.createInvite')}</Button>
      {url && <CopyLink url={url} valid={t('common.days7')} />}
    </form>
  )
}

function UserRow({ user, roleNames }) {
  const { t, tError } = useT()
  const qc = useQueryClient()
  const [error, setError] = useState(null)
  const [recoveryUrl, setRecoveryUrl] = useState(null)
  const refresh = () => qc.invalidateQueries({ queryKey: ['admin', 'users'] })
  const unlock = useMutation({ mutationFn: () => send('POST', `/admin/users/${user.id}/unlock`), onSuccess: refresh })
  const setRoles = useMutation({
    mutationFn: (roles) => send('PUT', `/admin/users/${user.id}/roles`, { roles }),
    onSuccess: refresh,
    onError: (e) => setError(tError(e)),
  })
  const recovery = async () => setRecoveryUrl((await send('POST', `/admin/users/${user.id}/recovery-link`)).url)
  const toggle = (role) =>
    setRoles.mutate(user.roles.includes(role) ? user.roles.filter((r) => r !== role) : [...user.roles, role])

  return (
    <li className="rounded-xl bg-white p-3 text-left shadow-sm">
      <div className="flex items-center justify-between gap-2">
        <span className="font-bold">{user.display_name}</span>
        <span className="text-xs text-rose-400">{user.username || '—'} · {t(user.has_passkey ? 'admin.hasPasskey' : 'admin.noPasskey')}</span>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        {roleNames.map((role) => (
          <label key={role} className="flex items-center gap-1 text-sm">
            <input type="checkbox" checked={user.roles.includes(role)} onChange={() => toggle(role)} /> {role}
          </label>
        ))}
        <button onClick={recovery} className="rounded-full bg-rose-100 px-3 py-1 text-xs font-bold">{t('admin.recoveryLink')}</button>
        {user.locked && (
          <button onClick={() => unlock.mutate()} className="ml-auto rounded-full bg-amber-400 px-3 py-1 text-xs font-bold">
            {t('admin.unlockPin')}
          </button>
        )}
      </div>
      {recoveryUrl && <CopyLink url={recoveryUrl} valid={t('common.hours24')} />}
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </li>
  )
}

export default function Admin() {
  const { t } = useT()
  const { data: me } = useMe()
  const users = useQuery({ queryKey: ['admin', 'users'], queryFn: () => api('/admin/users') })
  const roles = useQuery({ queryKey: ['admin', 'roles'], queryFn: () => api('/admin/roles') })

  if (!me.permissions.includes('manage_users')) return <Navigate to="/" replace />

  return (
    <main className="min-h-[85vh] bg-rose-50 p-4 font-sans text-rose-900">
      <div className="mx-auto flex max-w-md flex-col gap-5">
        <div className="flex items-center justify-between">
          <h1 className="font-display text-3xl italic text-rose-600">{t('admin.title')}</h1>
          <Link to="/" className="text-sm text-rose-500 underline">{t('common.back')}</Link>
        </div>
        <InviteForm />
        {users.data && <p className="text-sm text-rose-400">{t('admin.users', { count: users.data.length })}</p>}
        <ul className="flex flex-col gap-2">
          {users.data?.map((u) => <UserRow key={u.id} user={u} roleNames={roles.data?.map((r) => r.name) ?? []} />)}
        </ul>
        <SpacesAdmin users={users.data} />
        <BackupCard />
        <ExportCard />
      </div>
    </main>
  )
}
