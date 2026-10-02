import { useSpaces } from '../spaces.jsx'
import Bell from './Bell.jsx'

// Top bar: which space I'm in + notifications. Navigation lives in the bottom tab bar.
export default function Header() {
  const { spaces, active, setActive } = useSpaces()

  return (
    <header className="sticky top-0 z-10 flex items-center gap-3 bg-white/90 px-4 py-3 font-sans shadow-sm backdrop-blur">
      {spaces.length > 0 && (
        <select value={active?.id ?? ''} onChange={(e) => setActive(Number(e.target.value))}
          className="rounded-full bg-rose-100 px-3 py-1 text-sm font-bold text-rose-700">
          {spaces.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
      )}
      <span className="font-display italic text-rose-600">Thisissus 💌</span>
      <Bell />
    </header>
  )
}
