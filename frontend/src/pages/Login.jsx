import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Navigate } from 'react-router-dom'
import { loginWithPasskey, useMe } from '../auth.js'
import Screen, { Button } from '../components/Screen.jsx'

export default function Login() {
  const { data: me } = useMe()
  const qc = useQueryClient()
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  if (me) return <Navigate to="/" replace />

  async function onLogin() {
    setBusy(true)
    setError(null)
    try {
      qc.setQueryData(['me'], await loginWithPasskey())
    } catch (e) {
      setError(e.code || e.name)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Screen title="Thisissus 💌">
      <Button onClick={onLogin} disabled={busy}>Prijava s passkey</Button>
      {error && <p className="text-sm text-red-600">Prijava ni uspela ({error})</p>}
    </Screen>
  )
}
