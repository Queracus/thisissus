import { useMemo } from 'react'

// The original "Greva na dejt?" look: floating hearts behind a frosted card that pops in.
export function FloatingHearts({ count = 14 }) {
  const hearts = useMemo(() => Array.from({ length: count }, (_, i) => ({
    left: `${(i * 37) % 100}%`,
    duration: `${9 + ((i * 7) % 9)}s`,
    delay: `-${(i * 3) % 12}s`,
    size: `${1 + ((i * 5) % 10) / 10}rem`,
  })), [count])

  return (
    <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden" aria-hidden>
      {hearts.map((h, i) => (
        <span key={i} className="absolute animate-float-up text-rose-400"
          style={{ left: h.left, animationDuration: h.duration, animationDelay: h.delay, fontSize: h.size }}>
          ♥
        </span>
      ))}
    </div>
  )
}

export default function InviteCard({ children }) {
  return (
    <main className="relative flex min-h-[85vh] items-center justify-center bg-gradient-to-b from-rose-50 to-pink-100 p-4 font-sans text-rose-900">
      <FloatingHearts />
      <div className="relative z-10 flex w-full max-w-md animate-pop-in flex-col items-center gap-5 rounded-3xl bg-white/70 p-6 text-center shadow-xl backdrop-blur">
        {children}
      </div>
    </main>
  )
}

export function BigButton({ variant = 'yes', ...props }) {
  const style = variant === 'yes'
    ? 'bg-gradient-to-br from-rose-600 to-pink-400 text-white'
    : 'bg-gradient-to-br from-violet-200 to-violet-300 text-violet-900'
  return <button {...props} className={`rounded-full px-7 py-3 text-lg font-bold shadow-lg active:scale-95 disabled:opacity-50 ${style}`} />
}
