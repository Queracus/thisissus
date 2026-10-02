import { useQueryClient } from '@tanstack/react-query'
import { logout, useMe } from '../auth.js'
import Screen, { Button } from '../components/Screen.jsx'
import { useT } from '../i18n/index.jsx'
import { useSpaces } from '../spaces.jsx'

export default function Home() {
  const { data: me } = useMe()
  const { active } = useSpaces()
  const { t } = useT()
  const qc = useQueryClient()

  async function onLogout() {
    await logout()
    qc.setQueryData(['me'], null)
  }

  return (
    <Screen title={t('app.title')}>
      <p>{t('home.hello', { name: me.display_name })}</p>
      {!active && <p className="max-w-xs text-sm">{t('space.none')}</p>}
      <Button onClick={onLogout}>{t('home.logout')}</Button>
    </Screen>
  )
}
