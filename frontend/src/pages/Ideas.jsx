import { Link, useSearchParams } from 'react-router-dom'
import SurprisePicker from '../components/SurprisePicker.jsx'
import { TagChips } from '../components/Tags.jsx'
import { formatCost } from '../dates.js'
import { SEASON_EMOJI, useIdeas } from '../ideas.js'
import { useT } from '../i18n/index.jsx'

export default function Ideas() {
  const { t, locale } = useT()
  const [params] = useSearchParams()
  const archived = params.get('archived') === 'true'
  const { data: ideas = [], isLoading } = useIdeas(archived)

  return (
    <main className="min-h-[85vh] bg-rose-50 p-4 font-sans text-rose-900">
      <div className="mx-auto flex max-w-md flex-col gap-3">
        <div className="flex items-center justify-between">
          <h1 className="font-display text-3xl italic text-rose-600">{t(archived ? 'ideas.archiveTitle' : 'ideas.title')}</h1>
          <Link to={archived ? '/ideas' : '/ideas?archived=true'} className="text-sm text-rose-500 underline">{t(archived ? 'ideas.showOpen' : 'ideas.showArchive')}</Link>
        </div>
        {!archived && <div className="flex gap-2"><SurprisePicker /><Link to="/calendar" className="self-start rounded-full bg-white px-4 py-2 text-sm font-bold shadow-sm">📅 {t('calendar.title')}</Link></div>}
        {!isLoading && ideas.length === 0 && <p className="py-10 text-center text-sm">{t('ideas.empty')}</p>}
        {ideas.map((i) => (
          <Link key={i.id} to={`/ideas/${i.id}`} className="rounded-2xl bg-white p-4 shadow-sm active:scale-[0.99]">
            <div className="flex items-center justify-between gap-2">
              <span className="font-bold">{i.season && SEASON_EMOJI[i.season]} {i.title}</span>
              <span className="text-xs text-rose-400">{i.times_done > 0 && `🎉${i.times_done}× · `}{t(`ideas.status.${i.status}`)}</span>
            </div>
            <div className="mt-1 flex justify-between text-xs text-rose-400">
              <span>{t('ideas.suggestedBy', { name: i.suggested_by_name ?? '?' })}</span>
              <span>{formatCost(locale, i.est_cost)}</span>
            </div>
            {i.tags.length > 0 && <div className="mt-2"><TagChips tags={i.tags} /></div>}
          </Link>
        ))}
      </div>
      <Link to="/ideas/new" aria-label={t('ideas.new')}
        className="fixed bottom-6 right-6 flex h-14 w-14 items-center justify-center rounded-full bg-rose-500 text-3xl text-white shadow-lg active:scale-95">
        +
      </Link>
    </main>
  )
}
