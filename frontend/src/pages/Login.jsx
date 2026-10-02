import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Navigate } from 'react-router-dom'
import { loginWithPasskey, loginWithPin, useMe } from '../auth.js'
import Screen, { Button, Input, LinkButton } from '../components/Screen.jsx'

function errorText(e) {
  if (e.code === 'auth.pin_locked') return `Preveč napak. Poskusi čez ${Math.ceil(e.body.retry_after / 60)} min.`
  if (e.code === 'auth.pin_invalid') return 'Napačno ime ali PIN.'
  return `Prijava ni uspela (${e.code || e.name})`
}

export default function Login() {
  const { data: me } = useMe()
  const qc = useQueryClient()
  const [usePin, setUsePin] = useState(false)
  const [username, setUsername] = useState('')
  const [pin, setPin] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  if (me) return <Navigate to="/" replace />

  async function attempt(login) {
    setBusy(true)
    setError(null)
    try {
      qc.setQueryData(['me'], await login())
    } catch (e) {
      setError(errorText(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Screen title="Thisissus 💌">
      {usePin ? (
        <form className="flex flex-col items-center gap-3" onSubmit={(e) => { e.preventDefault(); attempt(() => loginWithPin(username, pin)) }}>
          <Input placeholder="Uporabniško ime" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} />
          <Input placeholder="PIN" inputMode="numeric" maxLength={6} autoComplete="current-password" type="password" value={pin} onChange={(e) => setPin(e.target.value)} />
          <Button type="submit" disabled={busy}>Prijava s PIN</Button>
          <LinkButton type="button" onClick={() => setUsePin(false)}>Nazaj na passkey</LinkButton>
        </form>
      ) : (
        <>
          <Button onClick={() => attempt(loginWithPasskey)} disabled={busy}>Prijava s passkey</Button>
          <LinkButton onClick={() => setUsePin(true)}>Uporabi PIN</LinkButton>
        </>
      )}
      {error && <p className="text-sm text-red-600">{error}</p>}
    </Screen>
  )
}
