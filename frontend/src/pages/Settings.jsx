import { useState } from 'react'
import { Link } from 'react-router-dom'
import { setPin } from '../auth.js'
import Devices from '../components/Devices.jsx'
import Screen, { Button, Input } from '../components/Screen.jsx'

export default function Settings() {
  const [username, setUsername] = useState('')
  const [pin, setPinValue] = useState('')
  const [msg, setMsg] = useState(null)

  async function onSave(e) {
    e.preventDefault()
    try {
      await setPin(username, pin)
      setMsg('PIN shranjen ✓')
    } catch (err) {
      setMsg(err.code === 'auth.username_taken' ? 'Ime je že zasedeno.' : 'Ime: 3–30 znakov, PIN: 6 številk.')
    }
  }

  return (
    <Screen title="Nastavitve">
      <form className="flex flex-col items-center gap-3" onSubmit={onSave}>
        <p className="text-sm">PIN je rezervna prijava, če passkey ni na voljo.</p>
        <Input placeholder="Uporabniško ime" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} />
        <Input placeholder="6-mestni PIN" inputMode="numeric" maxLength={6} type="password" autoComplete="new-password" value={pin} onChange={(e) => setPinValue(e.target.value)} />
        <Button type="submit">Shrani PIN</Button>
        {msg && <p className="text-sm">{msg}</p>}
      </form>
      <Devices />
      <Link to="/" className="text-sm text-rose-500 underline">Nazaj</Link>
    </Screen>
  )
}
