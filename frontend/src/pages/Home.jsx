import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../api.js'
import { useMe } from '../auth.js'
import { mediaUrl } from '../components/Photos.jsx'
import { TagChips } from '../components/Tags.jsx'
import { formatCost, formatWhen } from '../dates.js'
import { useT } from '../i18n/index.jsx'
import { useSpaces } from '../spaces.jsx'

function Card({ title, children }) {
  return (
    <section className="flex flex-col gap-2 rounded-2xl bg-white p-4 shadow-sm">
      <h2 className="font-bold text-rose-600">{title}</h2>
      {children}
    </section>
  )
}

function MonthBars({ months, locale }) {
  const max = Math.max(1, ...months.map((m) => m.count))
  return (
    <div className="flex h-24 items-end gap-1">
      {months.map((m) => (
        <div key={m.month} className="flex flex-1 flex-col items-center gap-1">
          <div className="w-full rounded-t bg-rose-400" style={{ height: `${(m.count / max) * 72}px` }} title={`${m.count}`} />
          <span className="text-[9px] text-rose-400">{new Date(`${m.month}-01`).toLocaleDateString(locale, { month: 'short' })}</span>
        </div>
      ))}
    </div>
  )
}

export default function Home() {
  const { t, locale } = useT()
  const { data: me } = useMe()
  const { active } = useSpaces()
  const { data: d } = useQuery({ queryKey: ['dashboard', active?.id], queryFn: () => api('/dashboard'), enabled: !!active })

  return (
    <main className="min-h-[85vh] bg-rose-50 p-4 pb-24 font-sans text-rose-900">
      <div className="mx-auto flex max-w-md flex-col gap-3">
        <h1 className="font-display text-3xl italic text-rose-600">{t('home.hello', { name: me.display_name })}</h1>
        {!active && <p className="text-sm">{t('space.none')}</p>}
        <div className="flex gap-2">
          <Link to="/ideas/new" className="flex-1 rounded-2xl bg-gradient-to-br from-rose-600 to-pink-400 p-3 text-center font-bold text-white shadow">💡 {t('ideas.new')}</Link>
          <Link to="/dates/new" className="flex-1 rounded-2xl bg-white p-3 text-center font-bold shadow-sm">💕 {t('dates.new')}</Link>
        </div>
        {d?.awaiting_me.length > 0 && (
          <Card title={`⏳ ${t('dashboard.awaiting')}`}>
            {d.awaiting_me.map((a) => (
              <Link key={a.id} to={`/ideas/${a.id}`} className="rounded-xl bg-rose-50 p-2 text-sm">
                <b>{a.title}</b> · {t('proposals.askedBy', { name: a.proposed_by_name })}
              </Link>
            ))}
          </Card>
        )}
        {d?.upcoming.length > 0 && (
          <Card title={`📅 ${t('dashboard.upcoming')}`}>
            {d.upcoming.map((u) => (
              <Link key={u.id} to={`/ideas/${u.id}`} className="flex justify-between text-sm"><b>{u.title}</b><span>{formatWhen(locale, u.scheduled_at)}</span></Link>
            ))}
          </Card>
        )}
        {d?.on_this_day.length > 0 && (
          <Card title={`✨ ${t('dashboard.onThisDay')}`}>
            {d.on_this_day.map((m) => (
              <Link key={m.id} to={`/dates/${m.id}`} className="flex items-center gap-3">
                {m.thumb_id && <img src={mediaUrl(m.thumb_id, 'thumb')} alt="" className="h-16 w-16 rounded-xl object-cover" />}
                <span className="text-sm"><b>{m.title}</b><br /><span className="text-rose-400">{t('dashboard.yearsAgo', { count: m.years_ago })}</span></span>
              </Link>
            ))}
          </Card>
        )}
        {d && (
          <Card title={`📊 ${t('dashboard.stats')}`}>
            <div className="grid grid-cols-3 gap-2 text-center text-sm">
              <div><div className="text-2xl font-bold">{d.stats.this_year}</div>{t('dashboard.thisYear')}</div>
              <div><div className="text-2xl font-bold">{d.stats.total}</div>{t('dashboard.total')}</div>
              <div><div className="text-lg font-bold">{formatCost(locale, d.stats.spent_this_year)}</div>{t('dashboard.spent')}</div>
            </div>
            {d.stats.per_month.length > 0 && <MonthBars months={d.stats.per_month} locale={locale} />}
            {d.stats.top_tags.length > 0 && <TagChips tags={d.stats.top_tags} />}
            <Link to="/map" className="text-sm text-rose-500 underline">🗺 {t('map.title')}</Link>
          </Card>
        )}
      </div>
    </main>
  )
}
