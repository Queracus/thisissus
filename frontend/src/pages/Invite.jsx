import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router-dom'
import { registerPasskey } from '../auth.js'
import Screen, { Button } from '../components/Screen.jsx'

export default function Invite() {
  const { token } = useParams()
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  async function onRegister() {
    setBusy(true)
    setError(null)
    try {
      qc.setQueryData(['me'], await registerPasskey(token))
      navigate('/', { replace: true })
    } catch (e) {
      setError(e.code || e.name)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Screen title="Dobrodošla 💌">
      <p>Ustvari passkey (Face ID / prstni odtis) za prijavo.</p>
      <Button onClick={onRegister} disabled={busy}>Ustvari passkey</Button>
      {error && <p className="text-sm text-red-600">Ni uspelo ({error})</p>}
    </Screen>
  )
}
