import { useQuery } from '@tanstack/react-query'
import { api } from './api.js'
import { useSpaces } from './spaces.jsx'

export function useRecipes(status) {
  const { active } = useSpaces()
  return useQuery({ queryKey: ['recipes', active?.id, status], queryFn: () => api(`/recipes?status=${status}`), enabled: !!active })
}

export const useRecipe = (id) =>
  useQuery({
    queryKey: ['recipe', id],
    queryFn: () => api(`/recipes/${id}`),
    enabled: !!id,
    refetchInterval: (q) => (q.state.data?.photos?.some((p) => p.status === 'pending') ? 3000 : false),
  })

// 1.5 → "1,5" in sl; trims trailing zeros.
export const formatAmount = (locale, amount) =>
  amount == null ? '' : new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(amount)
