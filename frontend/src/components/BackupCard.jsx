import { useQuery } from '@tanstack/react-query'
import { api } from '../api.js'
import { useT } from '../i18n/index.jsx'

// Admin: is last night's backup there, recent, and is the USB drive filling up?
export default function BackupCard() {
  const { t, locale } = useT()
  const { data: s } = useQuery({ queryKey: ['admin', 'backup'], queryFn: () => api('/admin/backup-status'), refetchInterval: 600000 })
  if (!s) return null
  const good = s.ok && s.warnings.length === 0

  return (
    <section className={`flex flex-col gap-1 rounded-2xl p-4 text-sm shadow-sm ${good ? 'bg-emerald-50' : 'bg-amber-50'}`}>
      <h2 className="font-bold">💾 {t('backup.title')}</h2>
      {s.time && (
        <p>{t(s.ok ? 'backup.lastOk' : 'backup.lastFailed', { when: new Date(s.time).toLocaleString(locale) })}
          {s.size != null && ` · ${(s.size / 1048576).toFixed(1)} MB`}{s.disk_used_pct != null && ` · USB ${s.disk_used_pct} %`}</p>
      )}
      {s.warnings.map((w) => <p key={w} className="font-bold text-amber-700">⚠ {t(`error.${w}`)}</p>)}
    </section>
  )
}
