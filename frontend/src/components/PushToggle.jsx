import { useEffect, useState } from 'react'
import { useT } from '../i18n/index.jsx'
import { currentSubscription, disablePush, enablePush, needsHomeScreen, pushSupported } from '../push.js'

export default function PushToggle() {
  const { t } = useT()
  const [on, setOn] = useState(null)
  const [msg, setMsg] = useState(null)

  useEffect(() => { currentSubscription().then((s) => setOn(!!s)).catch(() => setOn(false)) }, [])

  if (needsHomeScreen()) return <p className="max-w-xs text-sm">📲 {t('push.iosHint')}</p>
  if (!pushSupported()) return <p className="max-w-xs text-sm">{t('push.unsupported')}</p>

  async function toggle() {
    setMsg(null)
    try {
      if (on) await disablePush()
      else await enablePush()
      setOn(!on)
    } catch (e) {
      setMsg(t(e.code === 'push.denied' ? 'push.denied' : 'push.failed'))
    }
  }

  return (
    <div className="flex flex-col items-center gap-1">
      <button onClick={toggle} disabled={on === null} className={`rounded-full px-5 py-2 text-sm font-bold shadow-sm ${on ? 'bg-rose-500 text-white' : 'bg-white'}`}>
        🔔 {t(on ? 'push.on' : 'push.off')}
      </button>
      {msg && <p className="max-w-xs text-xs text-red-600">{msg}</p>}
    </div>
  )
}
