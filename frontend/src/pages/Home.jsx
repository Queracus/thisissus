import { useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { logout, useMe } from '../auth.js'
import Screen, { Button } from '../components/Screen.jsx'

export default function Home() {
  const { data: me } = useMe()
  const qc = useQueryClient()

  async function onLogout() {
    await logout()
    qc.setQueryData(['me'], null)
  }

  return (
    <Screen title="Thisissus 💌">
      <p>Živjo, {me.display_name}!</p>
      <Link to="/settings" className="text-sm text-rose-500 underline">Nastavitve</Link>
      <Button onClick={onLogout}>Odjava</Button>
    </Screen>
  )
}
