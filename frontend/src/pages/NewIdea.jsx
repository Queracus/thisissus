import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '../api.js'
import IdeaFields, { emptyIdea, formToBody } from '../components/IdeaFields.jsx'
import InviteCard, { BigButton } from '../components/InviteCard.jsx'
import { useT } from '../i18n/index.jsx'

// The original invite page, reborn: step 1 asks "Greva na …?", step 2 adds details.
export default function NewIdea() {
  const { t, tError } = useT()
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [v, setV] = useState(emptyIdea)
  const [error, setError] = useState(null)

  async function onSave(e) {
    e.preventDefault()
    try {
      const idea = await api('/ideas', { method: 'POST', body: JSON.stringify(formToBody(v)) })
      qc.invalidateQueries({ queryKey: ['ideas'] })
      navigate(`/ideas/${idea.id}`, { replace: true })
    } catch (err) {
      setError(tError(err))
    }
  }

  return (
    <InviteCard>
      {step === 1 ? (
        <form className="flex w-full flex-col items-center gap-5" onSubmit={(e) => { e.preventDefault(); setStep(2) }}>
          <h1 className="font-display text-4xl italic text-rose-600">{t('ideas.ask')}</h1>
          <input autoFocus required value={v.title} onChange={(e) => setV({ ...v, title: e.target.value })} placeholder={t('ideas.askPlaceholder')}
            className="w-full border-b-2 border-rose-300 bg-transparent py-2 text-center font-display text-2xl italic text-rose-700 outline-none placeholder:text-rose-300" />
          <BigButton type="submit" disabled={!v.title.trim()}>{t('ideas.next')} 💕</BigButton>
        </form>
      ) : (
        <form className="flex w-full flex-col items-center gap-4" onSubmit={onSave}>
          <h2 className="font-display text-3xl italic text-rose-600">{v.title}?</h2>
          <p className="text-sm">{t('ideas.detailsHint')}</p>
          <IdeaFields value={v} onChange={setV} withTitle={false} />
          <div className="flex gap-3">
            <BigButton type="button" variant="back" onClick={() => setStep(1)}>{t('common.back')}</BigButton>
            <BigButton type="submit">{t('ideas.save')}</BigButton>
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
        </form>
      )}
    </InviteCard>
  )
}
