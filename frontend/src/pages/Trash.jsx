import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api.js'
import { useT } from '../i18n/index.jsx'
import { useSpaces } from '../spaces.jsx'

const TRASH_DAYS = 30

export default function Trash() {
  const { t } = useT()
  const { active } = useSpaces()
  const qc = useQueryClient()
  const { data: items = [] } = useQuery({ queryKey: ['trash', active?.id], queryFn: () => api('/trash'), enabled: !!active })

  async function act(item, method, path) {
    if (method === 'DELETE' && !confirm(t('trash.confirmPurge'))) return
    await api(`/trash/${item.type}/${item.id}${path}`, { method })
    for (const key of ['trash', 'dates', 'date', 'map']) qc.invalidateQueries({ queryKey: [key] })
  }

  const daysLeft = (deletedAt) => Math.max(0, TRASH_DAYS - Math.floor((Date.now() - new Date(deletedAt)) / 86400000))

  return (
    <main className="min-h-[85vh] bg-rose-50 p-4 font-sans text-rose-900">
      <div className="mx-auto flex max-w-md flex-col gap-3">
        <h1 className="font-display text-3xl italic text-rose-600">{t('trash.title')}</h1>
        <p className="text-sm text-rose-400">{t('trash.info')}</p>
        {items.length === 0 && <p className="py-10 text-center text-sm">{t('trash.empty')}</p>}
        {items.map((i) => (
          <div key={`${i.type}-${i.id}`} className="flex items-center justify-between gap-2 rounded-2xl bg-white p-4 shadow-sm">
            <div>
              <div className="font-bold">{t(`trash.type.${i.type}`)}: {i.label}</div>
              <div className="text-xs text-rose-400">{t('trash.daysLeft', { count: daysLeft(i.deleted_at) })}</div>
            </div>
            <div className="flex flex-col items-end gap-1 text-sm">
              <button onClick={() => act(i, 'POST', '/restore')} className="font-bold text-rose-600 underline">{t('trash.restore')}</button>
              <button onClick={() => act(i, 'DELETE', '')} className="text-xs text-red-600 underline">{t('trash.purge')}</button>
            </div>
          </div>
        ))}
      </div>
    </main>
  )
}
