import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api.js'
import PinPicker from '../components/PinPicker.jsx'
import { Button } from '../components/Screen.jsx'
import { TagPicker } from '../components/Tags.jsx'
import { fromLocalInput, toLocalInput, useDate } from '../dates.js'
import { useT } from '../i18n/index.jsx'

const field = 'w-full rounded-xl border border-rose-200 bg-white px-4 py-3 outline-rose-400'

function Form({ initial }) {
  const { t, tError } = useT()
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [v, setV] = useState({
    title: initial?.title ?? '',
    starts_at: toLocalInput(initial?.starts_at),
    ends_at: toLocalInput(initial?.ends_at),
    place_name: initial?.place_name ?? '',
    cost: initial?.cost ?? '',
  })
  const [tagIds, setTagIds] = useState(initial?.tags.map((tag) => tag.id) ?? [])
  const [pin, setPin] = useState({ lat: initial?.lat ?? null, lon: initial?.lon ?? null })
  const [multiDay, setMultiDay] = useState(!!initial?.ends_at)
  const [error, setError] = useState(null)
  const set = (k) => (e) => setV({ ...v, [k]: e.target.value })

  async function onSave(e) {
    e.preventDefault()
    setError(null)
    const body = {
      title: v.title,
      starts_at: fromLocalInput(v.starts_at),
      ends_at: multiDay ? fromLocalInput(v.ends_at) : null,
      place_name: v.place_name || null,
      cost: v.cost === '' ? null : Number(v.cost),
      lat: pin.lat,
      lon: pin.lon,
      tag_ids: tagIds,
    }
    try {
      const saved = await api(initial ? `/dates/${initial.id}` : '/dates', { method: initial ? 'PUT' : 'POST', body: JSON.stringify(body) })
      qc.invalidateQueries({ queryKey: ['dates'] })
      qc.setQueryData(['date', String(saved.id)], saved)
      navigate(`/dates/${saved.id}`, { replace: true })
    } catch (err) {
      setError(err.code === 'validation.invalid' ? t('dates.invalid', { fields: err.body.fields.map((f) => t(`dates.field.${f}`)).join(', ') }) : tError(err))
    }
  }

  return (
    <form onSubmit={onSave} className="mx-auto flex max-w-md flex-col gap-3">
      <h1 className="font-display text-3xl italic text-rose-600">{t(initial ? 'dates.edit' : 'dates.new')}</h1>
      <label className="text-sm">{t('dates.field.title')}<input required className={field} value={v.title} onChange={set('title')} /></label>
      <label className="text-sm">{t('dates.field.starts_at')}<input required type="datetime-local" className={field} value={v.starts_at} onChange={set('starts_at')} /></label>
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={multiDay} onChange={(e) => setMultiDay(e.target.checked)} />{t('dates.multiDay')}</label>
      {multiDay && <label className="text-sm">{t('dates.field.ends_at')}<input required type="datetime-local" className={field} value={v.ends_at} onChange={set('ends_at')} /></label>}
      <label className="text-sm">{t('dates.field.place_name')}<input className={field} value={v.place_name} onChange={set('place_name')} /></label>
      <label className="text-sm">{t('dates.field.cost')}<input type="number" min="0" step="0.01" inputMode="decimal" className={field} value={v.cost} onChange={set('cost')} /></label>
      <div className="text-sm">{t('map.pin')}<PinPicker dateId={initial?.id} value={pin} onChange={setPin} /></div>
      <div className="text-sm">{t('tags.title')}<TagPicker value={tagIds} onChange={setTagIds} /></div>
      <Button type="submit">{t('dates.save')}</Button>
      {error && <p className="text-sm text-red-600">{error}</p>}
    </form>
  )
}

export default function DateForm() {
  const { id } = useParams()
  return (
    <main className="min-h-[85vh] bg-rose-50 p-4 font-sans text-rose-900">
      {id ? <EditLoader id={id} /> : <Form />}
    </main>
  )
}

function EditLoader({ id }) {
  const { data } = useDate(id)
  return data ? <Form initial={data} /> : null
}
