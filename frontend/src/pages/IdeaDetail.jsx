import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api.js'
import IdeaFields, { formToBody, ideaToForm } from '../components/IdeaFields.jsx'
import Negotiation from '../components/Negotiation.jsx'
import { Button } from '../components/Screen.jsx'
import { TagChips } from '../components/Tags.jsx'
import { formatCost } from '../dates.js'
import { SEASON_EMOJI, useIdea } from '../ideas.js'
import { useT } from '../i18n/index.jsx'

function EditForm({ idea, onDone }) {
  const { t, tError } = useT()
  const qc = useQueryClient()
  const [v, setV] = useState(ideaToForm(idea))
  const [error, setError] = useState(null)

  async function onSave(e) {
    e.preventDefault()
    try {
      qc.setQueryData(['idea', String(idea.id)], await api(`/ideas/${idea.id}`, { method: 'PUT', body: JSON.stringify(formToBody(v)) }))
      qc.invalidateQueries({ queryKey: ['ideas'] })
      onDone()
    } catch (err) {
      setError(tError(err))
    }
  }

  return (
    <form onSubmit={onSave} className="flex flex-col gap-3">
      <IdeaFields value={v} onChange={setV} />
      <Button type="submit">{t('ideas.save')}</Button>
      {error && <p className="text-sm text-red-600">{error}</p>}
    </form>
  )
}

export default function IdeaDetail() {
  const { id } = useParams()
  const { t, tError, locale } = useT()
  const qc = useQueryClient()
  const navigate = useNavigate()
  const { data: idea, error } = useIdea(id)
  const [editing, setEditing] = useState(false)

  async function onDelete() {
    if (!confirm(t('ideas.confirmDelete'))) return
    await api(`/ideas/${id}`, { method: 'DELETE' })
    qc.invalidateQueries({ queryKey: ['ideas'] })
    navigate('/ideas', { replace: true })
  }

  return (
    <main className="min-h-[85vh] bg-rose-50 p-4 font-sans text-rose-900">
      {error && <p className="text-center text-sm text-red-600">{tError(error)}</p>}
      {idea && (
        <article className="mx-auto flex max-w-md flex-col gap-3">
          <Link to="/ideas" className="text-sm text-rose-500 underline">← {t('ideas.title')}</Link>
          <h1 className="font-display text-3xl italic text-rose-600">{idea.title}</h1>
          <p className="text-sm text-rose-400">{t('ideas.suggestedBy', { name: idea.suggested_by_name ?? '?' })} · {t(`ideas.status.${idea.status}`)}</p>
          {editing ? <EditForm idea={idea} onDone={() => setEditing(false)} /> : (
            <>
              <TagChips tags={idea.tags} />
              {idea.description && <p className="whitespace-pre-line">{idea.description}</p>}
              {idea.url && <a href={idea.url} target="_blank" rel="noreferrer noopener" className="break-all text-rose-600 underline">🔗 {idea.url}</a>}
              {idea.est_cost != null && <p>💶 ~{formatCost(locale, idea.est_cost)}</p>}
              {idea.season && <p>{SEASON_EMOJI[idea.season]} {t(`ideas.season.${idea.season}`)}</p>}
              <Negotiation idea={idea} />
              <div className="mt-4 flex gap-4">
                <button onClick={() => setEditing(true)} className="text-sm text-rose-500 underline">{t('dates.edit')}</button>
                <button onClick={onDelete} className="text-sm text-red-600 underline">{t('dates.delete')}</button>
              </div>
            </>
          )}
        </article>
      )}
    </main>
  )
}
