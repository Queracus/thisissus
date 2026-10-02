import { useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api.js'
import { formatCost, formatWhen, useDate } from '../dates.js'
import Photos from '../components/Photos.jsx'
import Reviews, { Hearts } from '../components/Reviews.jsx'
import { TagChips } from '../components/Tags.jsx'
import { useT } from '../i18n/index.jsx'

export default function DateDetail() {
  const { id } = useParams()
  const { t, tError, locale } = useT()
  const qc = useQueryClient()
  const navigate = useNavigate()
  const { data: d, error } = useDate(id)

  async function onDelete() {
    if (!confirm(t('dates.confirmDelete'))) return
    await api(`/dates/${id}`, { method: 'DELETE' })
    qc.invalidateQueries({ queryKey: ['dates'] })
    navigate('/dates', { replace: true })
  }

  return (
    <main className="min-h-[85vh] bg-rose-50 p-4 font-sans text-rose-900">
      {error && <p className="text-center text-sm text-red-600">{tError(error)}</p>}
      {d && (
        <article className="mx-auto flex max-w-md flex-col gap-3">
          <Link to="/dates" className="text-sm text-rose-500 underline">← {t('dates.title')}</Link>
          <h1 className="font-display text-3xl italic text-rose-600">{d.title}</h1>
          <p className="text-sm text-rose-400">{formatWhen(locale, d.starts_at, d.ends_at)}</p>
          <TagChips tags={d.tags} />
          {d.place_name && <p>📍 {d.place_name}</p>}
          {d.cost != null && <p>💶 {formatCost(locale, d.cost)}</p>}
          {d.avg_rating != null && <p><Hearts value={d.avg_rating} /> <span className="text-sm text-rose-400">{d.avg_rating.toFixed(1)}</span></p>}
          <Photos date={d} />
          <Reviews date={d} />
          <div className="mt-4 flex gap-4">
            <Link to={`/dates/${d.id}/edit`} className="text-sm text-rose-500 underline">{t('dates.edit')}</Link>
            <button onClick={onDelete} className="text-sm text-red-600 underline">{t('dates.delete')}</button>
          </div>
        </article>
      )}
    </main>
  )
}
