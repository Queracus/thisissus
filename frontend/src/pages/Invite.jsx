import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router-dom'
import { registerPasskey } from '../auth.js'
import Screen, { Button } from '../components/Screen.jsx'
import { useT } from '../i18n/index.jsx'

// Invite (new user) and recovery (new passkey for an existing user) share this page.
export default function Invite({ recovery = false }) {
  const { token } = useParams()
  const { t, tError } = useT()
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
      setError(tError(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Screen title={t(recovery ? 'invite.newPasskey' : 'invite.welcome')}>
      <p>{t(recovery ? 'invite.recoveryText' : 'invite.welcomeText')}</p>
      <Button onClick={onRegister} disabled={busy}>{t('invite.create')}</Button>
      {error && <p className="text-sm text-red-600">{error}</p>}
    </Screen>
  )
}
