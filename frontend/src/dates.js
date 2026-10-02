import { useQuery } from '@tanstack/react-query'
import { api } from './api.js'
import { useSpaces } from './spaces.jsx'

// <input type="datetime-local"> works in local time without zone; the API speaks ISO instants.
export const toLocalInput = (iso) => {
  if (!iso) return ''
  const d = new Date(iso)
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
}
export const fromLocalInput = (value) => (value ? new Date(value).toISOString() : null)

export function formatWhen(locale, startsAt, endsAt) {
  const f = new Intl.DateTimeFormat(locale, { dateStyle: 'medium', timeStyle: 'short' })
  return endsAt ? f.formatRange(new Date(startsAt), new Date(endsAt)) : f.format(new Date(startsAt))
}

export const formatCost = (locale, cost) =>
  cost == null ? null : new Intl.NumberFormat(locale, { style: 'currency', currency: 'EUR' }).format(cost)

export function useDates() {
  const { active } = useSpaces()
  return useQuery({ queryKey: ['dates', active?.id], queryFn: () => api('/dates'), enabled: !!active })
}

export const useDate = (id) => useQuery({ queryKey: ['date', id], queryFn: () => api(`/dates/${id}`) })
