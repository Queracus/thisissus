import { useQuery } from '@tanstack/react-query'
import { api } from './api.js'
import { useSpaces } from './spaces.jsx'

export const SEASONS = ['spring', 'summer', 'autumn', 'winter']
export const SEASON_EMOJI = { spring: '🌸', summer: '☀️', autumn: '🍂', winter: '❄️' }

export function useIdeas() {
  const { active } = useSpaces()
  return useQuery({ queryKey: ['ideas', active?.id], queryFn: () => api('/ideas'), enabled: !!active })
}

export const useIdea = (id) => useQuery({ queryKey: ['idea', id], queryFn: () => api(`/ideas/${id}`) })
