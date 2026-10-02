import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Navigate, useLocation } from 'react-router-dom'
import { loginWithPasskey, loginWithPin, useMe } from '../auth.js'
import Screen, { Button, Input, LinkButton } from '../components/Screen.jsx'
import { useT } from '../i18n/index.jsx'

export default function Login() {
  const { data: me } = useMe()
  const { t, tError } = useT()
  const from = useLocation().state?.from || '/'
  const qc = useQueryClient()
  const [usePin, setUsePin] = useState(false)
  const [username, setUsername] = useState('')
  const [pin, setPin] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  if (me) return <Navigate to={from} replace />

  async function attempt(login) {
    setBusy(true)
    setError(null)
    try {
      qc.setQueryData(['me'], await login())
    } catch (e) {
      setError(tError(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Screen title={t('app.title')}>
      {usePin ? (
        <form className="flex flex-col items-center gap-3" onSubmit={(e) => { e.preventDefault(); attempt(() => loginWithPin(username, pin)) }}>
          <Input placeholder={t('login.username')} autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} />
          <Input placeholder={t('login.pin')} inputMode="numeric" maxLength={6} autoComplete="current-password" type="password" value={pin} onChange={(e) => setPin(e.target.value)} />
          <Button type="submit" disabled={busy}>{t('login.pinSubmit')}</Button>
          <LinkButton type="button" onClick={() => setUsePin(false)}>{t('login.backToPasskey')}</LinkButton>
        </form>
      ) : (
        <>
          <Button onClick={() => attempt(loginWithPasskey)} disabled={busy}>{t('login.passkey')}</Button>
          <LinkButton onClick={() => setUsePin(true)}>{t('login.usePin')}</LinkButton>
        </>
      )}
      {error && <p className="text-sm text-red-600">{error}</p>}
    </Screen>
  )
}
