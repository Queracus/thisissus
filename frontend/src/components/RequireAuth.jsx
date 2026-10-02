import { Navigate, useLocation } from 'react-router-dom'
import { useMe } from '../auth.js'
import { SpaceProvider } from '../spaces.jsx'
import Header from './Header.jsx'

// Logged-in pages: header with space switcher; otherwise redirect to login (and come back afterwards).
export default function RequireAuth({ children }) {
  const { data: me, isLoading } = useMe()
  const location = useLocation()
  if (isLoading) return null
  if (!me) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  return (
    <SpaceProvider>
      <Header />
      {children}
    </SpaceProvider>
  )
}
