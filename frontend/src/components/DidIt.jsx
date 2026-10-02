import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '../api.js'
import { useT } from '../i18n/index.jsx'
import { BigButton } from './InviteCard.jsx'

// "We did it!": turns the idea into a pre-filled Date We've Had and opens it for photos, ratings and notes.
export default function DidIt({ idea }) {
  const { t, tError } = useT()
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [keep, setKeep] = useState(true)
  const [error, setError] = useState(null)
  if (!['idea', 'scheduled'].includes(idea.status)) return null

  async function onDidIt() {
    try {
      const { date_id } = await api(`/ideas/${idea.id}/did-it`, { method: 'POST', body: JSON.stringify({ archive: !keep }) })
      for (const key of ['ideas', 'idea', 'dates', 'timeline']) qc.invalidateQueries({ queryKey: [key] })
      navigate(`/dates/${date_id}/edit`)
    } catch (err) {
      setError(tError(err))
    }
  }

  return (
    <div className="flex flex-col items-center gap-2 rounded-2xl bg-gradient-to-br from-rose-100 to-pink-50 p-4">
      <BigButton onClick={onDidIt}>{t('didIt.button')} 🎉</BigButton>
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={keep} onChange={(e) => setKeep(e.target.checked)} /> {t('didIt.keep')}
      </label>
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  )
}
