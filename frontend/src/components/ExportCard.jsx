import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api.js'
import { useT } from '../i18n/index.jsx'

// Admin: copy every original photo/video into a browsable folder on the server.
export default function ExportCard() {
  const { t, locale } = useT()
  const qc = useQueryClient()
  const { data } = useQuery({
    queryKey: ['admin', 'export'],
    queryFn: () => api('/admin/export'),
    refetchInterval: (q) => (q.state.data?.queued ? 5000 : false),
  })

  async function start() {
    await api('/admin/export', { method: 'POST' })
    qc.invalidateQueries({ queryKey: ['admin', 'export'] })
  }

  return (
    <section className="flex flex-col gap-2 rounded-2xl bg-white p-4 text-sm shadow-sm">
      <h2 className="font-bold">📁 {t('export.title')}</h2>
      <p className="text-xs text-rose-400">{t('export.info', { dir: data?.dir ?? '…' })}</p>
      <button onClick={start} disabled={data?.queued} className="self-start rounded-full bg-rose-500 px-4 py-2 font-bold text-white disabled:opacity-50">
        {t(data?.queued ? 'export.running' : 'export.start')}
      </button>
      {data?.last && (
        <p>{t('export.last', { when: new Date(data.last.finished_at).toLocaleString(locale), files: data.last.files, written: data.last.written })}</p>
      )}
      {data?.failed && <p className="text-xs text-red-600">{t('export.failed', { error: data.failed.last_error })}</p>}
    </section>
  )
}
