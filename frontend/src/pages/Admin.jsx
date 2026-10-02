import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, Navigate } from 'react-router-dom'
import { api } from '../api.js'
import { useMe } from '../auth.js'
import { Button, Input } from '../components/Screen.jsx'

const send = (method, path, body) => api(path, { method, body: JSON.stringify(body ?? {}) })

function InviteForm() {
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
      <Input placeholder="Ime novega uporabnika" value={name} onChange={(e) => setName(e.target.value)} />
      <Button type="submit" disabled={!name}>Ustvari povabilo</Button>
      {url && (
        <button type="button" onClick={() => navigator.clipboard.writeText(url)} className="max-w-xs break-all text-xs text-rose-600 underline">
          {url} (klikni za kopiranje, velja 7 dni)
        </button>
      )}
    </form>
  )
}

function UserRow({ user, roleNames }) {
  const qc = useQueryClient()
  const [error, setError] = useState(null)
  const refresh = () => qc.invalidateQueries({ queryKey: ['admin', 'users'] })
  const unlock = useMutation({ mutationFn: () => send('POST', `/admin/users/${user.id}/unlock`), onSuccess: refresh })
  const setRoles = useMutation({
    mutationFn: (roles) => send('PUT', `/admin/users/${user.id}/roles`, { roles }),
    onSuccess: refresh,
    onError: (e) => setError(e.code === 'admin.last_admin' ? 'Vsaj en admin mora ostati.' : e.code),
  })
  const toggle = (role) =>
    setRoles.mutate(user.roles.includes(role) ? user.roles.filter((r) => r !== role) : [...user.roles, role])

  return (
    <li className="rounded-xl bg-white p-3 text-left shadow-sm">
      <div className="flex items-center justify-between gap-2">
        <span className="font-bold">{user.display_name}</span>
        <span className="text-xs text-rose-400">{user.username || '—'} · {user.has_passkey ? 'passkey ✓' : 'brez passkey'}</span>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        {roleNames.map((role) => (
          <label key={role} className="flex items-center gap-1 text-sm">
            <input type="checkbox" checked={user.roles.includes(role)} onChange={() => toggle(role)} /> {role}
          </label>
        ))}
        {user.locked && (
          <button onClick={() => unlock.mutate()} className="ml-auto rounded-full bg-amber-400 px-3 py-1 text-xs font-bold">
            Odkleni PIN
          </button>
        )}
      </div>
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </li>
  )
}

export default function Admin() {
  const { data: me } = useMe()
  const users = useQuery({ queryKey: ['admin', 'users'], queryFn: () => api('/admin/users') })
  const roles = useQuery({ queryKey: ['admin', 'roles'], queryFn: () => api('/admin/roles') })

  if (!me.permissions.includes('manage_users')) return <Navigate to="/" replace />

  return (
    <main className="min-h-screen bg-rose-50 p-4 font-sans text-rose-900">
      <div className="mx-auto flex max-w-md flex-col gap-5">
        <div className="flex items-center justify-between">
          <h1 className="font-display text-3xl italic text-rose-600">Admin</h1>
          <Link to="/" className="text-sm text-rose-500 underline">Nazaj</Link>
        </div>
        <InviteForm />
        <ul className="flex flex-col gap-2">
          {users.data?.map((u) => <UserRow key={u.id} user={u} roleNames={roles.data?.map((r) => r.name) ?? []} />)}
        </ul>
      </div>
    </main>
  )
}
