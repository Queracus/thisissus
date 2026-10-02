import { Link } from 'react-router-dom'
import { formatCost, formatWhen, useDates } from '../dates.js'
import { useT } from '../i18n/index.jsx'

export default function Dates() {
  const { t, locale } = useT()
  const { data: dates = [], isLoading } = useDates()

  return (
    <main className="min-h-[85vh] bg-rose-50 p-4 font-sans text-rose-900">
      <div className="mx-auto flex max-w-md flex-col gap-3">
        <div className="flex items-center justify-between">
          <h1 className="font-display text-3xl italic text-rose-600">{t('dates.title')}</h1>
          <span className="text-sm text-rose-400">{t('dates.count', { count: dates.length })}</span>
        </div>
        {!isLoading && dates.length === 0 && <p className="py-10 text-center text-sm">{t('dates.empty')}</p>}
        {dates.map((d) => (
          <Link key={d.id} to={`/dates/${d.id}`} className="rounded-2xl bg-white p-4 shadow-sm active:scale-[0.99]">
            <div className="font-bold">{d.title}</div>
            <div className="text-xs text-rose-400">{formatWhen(locale, d.starts_at, d.ends_at)}</div>
            <div className="mt-1 flex justify-between text-sm">
              <span>{d.place_name}</span>
              <span>{formatCost(locale, d.cost)}</span>
            </div>
          </Link>
        ))}
      </div>
      <Link to="/dates/new" aria-label={t('dates.new')}
        className="fixed bottom-6 right-6 flex h-14 w-14 items-center justify-center rounded-full bg-rose-500 text-3xl text-white shadow-lg active:scale-95">
        +
      </Link>
    </main>
  )
}
