import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../api.js'
import { useT } from '../i18n/index.jsx'
import { useSpaces } from '../spaces.jsx'

const dayKey = (d) => `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`

// Month grid (Monday first) of scheduled ideas.
export default function Calendar() {
  const { t, locale } = useT()
  const { active } = useSpaces()
  const [month, setMonth] = useState(() => { const d = new Date(); return new Date(d.getFullYear(), d.getMonth(), 1) })
  const next = new Date(month.getFullYear(), month.getMonth() + 1, 1)
  const { data: items = [] } = useQuery({
    queryKey: ['calendar', active?.id, month.toISOString()],
    queryFn: () => api(`/ideas/calendar?from=${encodeURIComponent(month.toISOString())}&to=${encodeURIComponent(next.toISOString())}`),
    enabled: !!active,
  })

  const byDay = {}
  for (const i of items) (byDay[dayKey(new Date(i.scheduled_at))] ??= []).push(i)
  const lead = (month.getDay() + 6) % 7
  const days = new Date(month.getFullYear(), month.getMonth() + 1, 0).getDate()
  const cells = [...Array(lead).fill(null), ...Array.from({ length: days }, (_, i) => new Date(month.getFullYear(), month.getMonth(), i + 1))]
  const weekdays = Array.from({ length: 7 }, (_, i) => new Date(2024, 0, 1 + i).toLocaleDateString(locale, { weekday: 'short' }))
  const today = dayKey(new Date())
  const shift = (n) => setMonth(new Date(month.getFullYear(), month.getMonth() + n, 1))

  return (
    <main className="min-h-[85vh] bg-rose-50 p-4 font-sans text-rose-900">
      <div className="mx-auto flex max-w-md flex-col gap-3">
        <div className="flex items-center justify-between">
          <button onClick={() => shift(-1)} className="px-3 text-2xl">‹</button>
          <h1 className="font-display text-2xl italic text-rose-600">{month.toLocaleDateString(locale, { month: 'long', year: 'numeric' })}</h1>
          <button onClick={() => shift(1)} className="px-3 text-2xl">›</button>
        </div>
        <div className="grid grid-cols-7 gap-1 text-center text-xs">
          {weekdays.map((w) => <div key={w} className="font-bold text-rose-400">{w}</div>)}
          {cells.map((d, i) => (
            <div key={i} className={`min-h-14 rounded-lg p-1 ${d ? 'bg-white' : ''} ${d && dayKey(d) === today ? 'ring-2 ring-rose-400' : ''}`}>
              {d && <div className="text-rose-300">{d.getDate()}</div>}
              {d && byDay[dayKey(d)]?.map((i) => (
                <Link key={i.id} to={`/ideas/${i.id}`} className="block truncate rounded bg-rose-500 px-1 text-[10px] text-white">{i.title}</Link>
              ))}
            </div>
          ))}
        </div>
        {items.length === 0 && <p className="text-center text-sm">{t('calendar.empty')}</p>}
      </div>
    </main>
  )
}
