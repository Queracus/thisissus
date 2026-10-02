import { NavLink } from 'react-router-dom'
import { useT } from '../i18n/index.jsx'

const TABS = [
  { to: '/', icon: '🏠', key: 'nav.home', end: true },
  { to: '/dates', icon: '💕', key: 'nav.dates' },
  { to: '/ideas', icon: '💡', key: 'nav.ideas' },
  { to: '/recipes', icon: '🍲', key: 'nav.recipes' },
  { to: '/more', icon: '☰', key: 'nav.more' },
]

// Phone-style tab bar; everything else lives under "Več".
export default function BottomNav() {
  const { t } = useT()
  return (
    <nav className="fixed inset-x-0 bottom-0 z-20 flex justify-around border-t border-rose-100 bg-white/95 pb-[env(safe-area-inset-bottom)] font-sans backdrop-blur">
      {TABS.map((tab) => (
        <NavLink key={tab.to} to={tab.to} end={tab.end}
          className={({ isActive }) => `flex flex-1 flex-col items-center py-2 text-[11px] ${isActive ? 'font-bold text-rose-600' : 'text-rose-400'}`}>
          <span className="text-xl leading-none">{tab.icon}</span>{t(tab.key)}
        </NavLink>
      ))}
    </nav>
  )
}
