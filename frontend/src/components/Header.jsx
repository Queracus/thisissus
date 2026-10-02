import { NavLink } from 'react-router-dom'
import { useMe } from '../auth.js'
import { useT } from '../i18n/index.jsx'
import { useSpaces } from '../spaces.jsx'

// Top bar: space switcher + navigation. Phone-first, wraps on narrow screens.
export default function Header() {
  const { t } = useT()
  const { data: me } = useMe()
  const { spaces, active, setActive } = useSpaces()
  const link = ({ isActive }) => `text-sm ${isActive ? 'font-bold text-rose-600' : 'text-rose-500'}`

  return (
    <header className="sticky top-0 z-10 flex flex-wrap items-center gap-x-4 gap-y-2 bg-white/90 px-4 py-3 font-sans shadow-sm backdrop-blur">
      {spaces.length > 0 && (
        <select value={active?.id ?? ''} onChange={(e) => setActive(Number(e.target.value))}
          className="rounded-full bg-rose-100 px-3 py-1 text-sm font-bold text-rose-700">
          {spaces.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
      )}
      <nav className="flex flex-wrap gap-4">
        <NavLink to="/" end className={link}>{t('nav.home')}</NavLink>
        {active && <NavLink to="/dates" className={link}>{t('nav.dates')}</NavLink>}
        {active && <NavLink to="/space" className={link}>{t('nav.space')}</NavLink>}
        <NavLink to="/settings" className={link}>{t('nav.settings')}</NavLink>
        {me.permissions.includes('manage_users') && <NavLink to="/admin" className={link}>{t('nav.admin')}</NavLink>}
      </nav>
    </header>
  )
}
