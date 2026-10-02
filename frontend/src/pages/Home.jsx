import { useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { logout, useMe } from '../auth.js'
import Screen, { Button } from '../components/Screen.jsx'
import { useT } from '../i18n/index.jsx'

export default function Home() {
  const { data: me } = useMe()
  const { t } = useT()
  const qc = useQueryClient()

  async function onLogout() {
    await logout()
    qc.setQueryData(['me'], null)
  }

  return (
    <Screen title={t('app.title')}>
      <p>{t('home.hello', { name: me.display_name })}</p>
      <Link to="/settings" className="text-sm text-rose-500 underline">{t('home.settings')}</Link>
      {me.permissions.includes('manage_users') && <Link to="/admin" className="text-sm text-rose-500 underline">{t('home.admin')}</Link>}
      <Button onClick={onLogout}>{t('home.logout')}</Button>
    </Screen>
  )
}
