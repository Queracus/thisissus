import { createContext, useContext, useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, setSpaceId } from './api.js'

const Spaces = createContext(null)
const KEY = 'thisissus.space'
const stored = () => { try { return Number(localStorage.getItem(KEY)) || null } catch { return null } }

// My spaces + the active one (remembered per browser). Must sit inside RequireAuth.
export function SpaceProvider({ children }) {
  const { data: spaces = [], isLoading } = useQuery({ queryKey: ['spaces'], queryFn: () => api('/spaces') })
  const [chosen, setChosen] = useState(stored)
  const active = spaces?.find((s) => s.id === chosen) ?? spaces?.[0] ?? null
  setSpaceId(active?.id ?? null)

  useEffect(() => { try { if (active) localStorage.setItem(KEY, active.id) } catch { /* storage blocked */ } }, [active])

  if (isLoading) return null
  return <Spaces.Provider value={{ spaces, active, setActive: setChosen }}>{children}</Spaces.Provider>
}

export const useSpaces = () => useContext(Spaces)
