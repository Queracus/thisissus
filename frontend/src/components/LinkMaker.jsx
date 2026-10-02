import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../api.js'
import { useT } from '../i18n/index.jsx'

const EXPIRY = ['1h', '1d', '1w']

// Secret read-only link for someone without an account. The URL is shown once — copy it now.
export default function LinkMaker({ scope, entityType, entityId }) {
  const { t, tError, locale } = useT()
  const qc = useQueryClient()
  const [expires, setExpires] = useState('1d')
  const [made, setMade] = useState(null)
  const [error, setError] = useState(null)

  async function make() {
    setError(null)
    try {
      const body = { scope, entity_type: entityType, expires_in: expires, ...(entityId && { entity_id: entityId }) }
      const res = await api('/shares/links', { method: 'POST', body: JSON.stringify(body) })
      setMade(res)
      await navigator.clipboard?.writeText(res.url).catch(() => {})
      qc.invalidateQueries({ queryKey: ['shares'] })
    } catch (err) {
      setError(tError(err))
    }
  }

  return (
    <div className="flex flex-col gap-2 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        🔗 {t('links.validFor')}
        {EXPIRY.map((e) => (
          <button key={e} type="button" onClick={() => setExpires(e)} className={`rounded-full px-3 py-1 ${expires === e ? 'bg-rose-500 text-white' : 'bg-rose-50'}`}>
            {t(`links.expiry.${e}`)}
          </button>
        ))}
        <button type="button" onClick={make} className="rounded-full bg-rose-600 px-3 py-1 font-bold text-white">{t('links.create')}</button>
      </div>
      {made && (
        <button type="button" onClick={() => navigator.clipboard?.writeText(made.url)} className="break-all rounded-xl bg-rose-50 p-2 text-left text-xs">
          {made.url}
          <span className="block text-rose-400">{t('links.copied', { until: new Date(made.expires_at).toLocaleString(locale, { dateStyle: 'short', timeStyle: 'short' }) })}</span>
        </button>
      )}
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  )
}
