import { Navigate } from 'react-router-dom'
import { useMe } from '../auth.js'

export default function RequireAuth({ children }) {
  const { data: me, isLoading } = useMe()
  if (isLoading) return null
  return me ? children : <Navigate to="/login" replace />
}
