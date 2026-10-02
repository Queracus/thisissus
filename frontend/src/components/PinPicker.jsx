import { useQuery } from '@tanstack/react-query'
import { api } from '../api.js'
import { useT } from '../i18n/index.jsx'
import LeafletMap from './LeafletMap.jsx'

// Optional map pin: tap the map to set it. On an existing date, offers the GPS from its photos.
export default function PinPicker({ dateId, value, onChange }) {
  const { t } = useT()
  const { data: suggestion } = useQuery({
    queryKey: ['suggested-location', dateId],
    queryFn: () => api(`/dates/${dateId}/suggested-location`),
    enabled: !!dateId,
  })
  const markers = value.lat != null ? [{ id: 'pin', lat: value.lat, lon: value.lon }] : []

  return (
    <div className="flex flex-col gap-2">
      <LeafletMap markers={markers} onPick={(lat, lon) => onChange({ lat, lon })} className="h-56" />
      <div className="flex gap-4 text-sm">
        {suggestion && (
          <button type="button" className="text-rose-500 underline" onClick={() => onChange({ lat: suggestion.lat, lon: suggestion.lon })}>
            📍 {t('map.useSuggestion')}
          </button>
        )}
        {value.lat != null && (
          <button type="button" className="text-rose-500 underline" onClick={() => onChange({ lat: null, lon: null })}>{t('map.clear')}</button>
        )}
      </div>
    </div>
  )
}
