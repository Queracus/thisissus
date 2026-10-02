import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api.js'
import Screen, { Button } from '../components/Screen.jsx'
import { useT } from '../i18n/index.jsx'
import { useSpaces } from '../spaces.jsx'

// Existing user accepts a space invite (/join/:token).
export default function Join() {
  const { token } = useParams()
  const { t, tError } = useT()
  const { setActive } = useSpaces()
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [error, setError] = useState(null)

  async function onJoin() {
    try {
      const { space_id } = await api('/spaces/join', { method: 'POST', body: JSON.stringify({ token }) })
      await qc.invalidateQueries({ queryKey: ['spaces'] })
      setActive(space_id)
      navigate('/', { replace: true })
    } catch (e) {
      setError(tError(e))
    }
  }

  return (
    <Screen title={t('app.title')}>
      <Button onClick={onJoin}>{t('space.join')}</Button>
      {error && <p className="text-sm text-red-600">{error}</p>}
    </Screen>
  )
}
