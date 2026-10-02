import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../api.js'
import { setPin, useMe } from '../auth.js'
import Devices from '../components/Devices.jsx'
import PushToggle from '../components/PushToggle.jsx'
import Screen, { Button, Input } from '../components/Screen.jsx'
import { LOCALES, useT } from '../i18n/index.jsx'

function LanguageSwitch() {
  const { t, locale } = useT()
  const { data: me } = useMe()
  const qc = useQueryClient()

  async function choose(next) {
    await api('/me/locale', { method: 'PUT', body: JSON.stringify({ locale: next }) })
    qc.setQueryData(['me'], { ...me, locale: next })
  }

  return (
    <div className="flex items-center gap-2 text-sm">
      {t('settings.language')}:
      {LOCALES.map((l) => (
        <button key={l} onClick={() => choose(l)} className={`rounded-full px-3 py-1 font-bold ${l === locale ? 'bg-rose-500 text-white' : 'bg-white'}`}>
          {l.toUpperCase()}
        </button>
      ))}
    </div>
  )
}

export default function Settings() {
  const { t, tError } = useT()
  const [username, setUsername] = useState('')
  const [pin, setPinValue] = useState('')
  const [msg, setMsg] = useState(null)

  async function onSave(e) {
    e.preventDefault()
    try {
      await setPin(username, pin)
      setMsg(t('settings.pinSaved'))
    } catch (err) {
      setMsg(tError(err))
    }
  }

  return (
    <Screen title={t('settings.title')}>
      <LanguageSwitch />
      <PushToggle />
      <form className="flex flex-col items-center gap-3" onSubmit={onSave}>
        <p className="text-sm">{t('settings.pinInfo')}</p>
        <Input placeholder={t('login.username')} autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} />
        <Input placeholder={t('settings.pinPlaceholder')} inputMode="numeric" maxLength={6} type="password" autoComplete="new-password" value={pin} onChange={(e) => setPinValue(e.target.value)} />
        <Button type="submit">{t('settings.savePin')}</Button>
        {msg && <p className="text-sm">{msg}</p>}
      </form>
      <Devices />
      <Link to="/" className="text-sm text-rose-500 underline">{t('common.back')}</Link>
    </Screen>
  )
}
