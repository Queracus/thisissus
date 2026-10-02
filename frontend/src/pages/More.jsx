import { useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { logout, useMe } from '../auth.js'
import { useT } from '../i18n/index.jsx'
import { useSpaces } from '../spaces.jsx'

export default function More() {
  const { t } = useT()
  const { data: me } = useMe()
  const { active } = useSpaces()
  const qc = useQueryClient()
  const links = [
    active && ['/calendar', '📅', 'calendar.title'],
    active && ['/map', '🗺', 'nav.map'],
    active && ['/shopping', '🛒', 'nav.shopping'],
    ['/shared', '👁', 'nav.shared'],
    active && ['/space', '🏡', 'nav.space'],
    active && ['/trash', '🗑', 'nav.trash'],
    ['/settings', '⚙️', 'nav.settings'],
    me.permissions.includes('manage_users') && ['/admin', '🔑', 'nav.admin'],
  ].filter(Boolean)

  async function onLogout() {
    await logout()
    qc.setQueryData(['me'], null)
  }

  return (
    <main className="min-h-[85vh] bg-rose-50 p-4 pb-24 font-sans text-rose-900">
      <div className="mx-auto flex max-w-md flex-col gap-2">
        {links.map(([to, icon, key]) => (
          <Link key={to} to={to} className="rounded-2xl bg-white p-4 font-bold shadow-sm">{icon} {t(key)}</Link>
        ))}
        <button onClick={onLogout} className="mt-4 rounded-2xl bg-white p-4 text-left font-bold text-red-600 shadow-sm">↩ {t('home.logout')}</button>
      </div>
    </main>
  )
}
