import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../api.js'
import { useT } from '../i18n/index.jsx'

export const mediaUrl = (id, variant) => `/api/media/${id}/${variant}`

// XHR instead of fetch: fetch cannot report upload progress.
function uploadFile(base, file, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `/api${base}/photos`)
    xhr.withCredentials = true
    xhr.upload.onprogress = (e) => e.lengthComputable && onProgress(e.loaded / e.total)
    xhr.onload = () => {
      const body = JSON.parse(xhr.responseText || '{}')
      xhr.status < 300 ? resolve(body) : reject(Object.assign(new Error(body.code), { code: body.code, body }))
    }
    xhr.onerror = () => reject(new Error('network'))
    const form = new FormData()
    form.append('file', file)
    xhr.send(form)
  })
}

function Uploader({ base, queryKey }) {
  const { t, tError } = useT()
  const qc = useQueryClient()
  const [items, setItems] = useState([])
  const update = (key, patch) => setItems((cur) => cur.map((i) => (i.key === key ? { ...i, ...patch } : i)))

  async function onPick(e) {
    const files = [...e.target.files]
    e.target.value = ''
    const batch = files.map((f, n) => ({ key: `${Date.now()}-${n}`, name: f.name, file: f, progress: 0, error: null }))
    setItems((cur) => [...cur, ...batch])
    for (const item of batch) {
      try {
        await uploadFile(base, item.file, (p) => update(item.key, { progress: p }))
        setItems((cur) => cur.filter((i) => i.key !== item.key))
        qc.invalidateQueries({ queryKey })
      } catch (err) {
        update(item.key, { error: tError(err) })
      }
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <label className="cursor-pointer self-start rounded-full bg-rose-500 px-4 py-2 text-sm font-bold text-white shadow active:scale-95">
        📷 {t('photos.add')}
        <input type="file" accept="image/*,video/*,.heic,.heif,.mov" multiple className="hidden" onChange={onPick} />
      </label>
      {items.map((i) => (
        <div key={i.key} className="text-xs">
          <div className="flex justify-between"><span className="truncate">{i.name}</span><span>{i.error ?? `${Math.round(i.progress * 100)}%`}</span></div>
          {!i.error && <div className="h-1 rounded bg-rose-100"><div className="h-1 rounded bg-rose-500" style={{ width: `${i.progress * 100}%` }} /></div>}
        </div>
      ))}
    </div>
  )
}

function Lightbox({ base, queryKey, photos, index, onClose }) {
  const { t } = useT()
  const qc = useQueryClient()
  const photo = photos[index]
  const [caption, setCaption] = useState(photo.caption ?? '')
  const refresh = () => qc.invalidateQueries({ queryKey })
  const send = (method, path, body) => api(path, { method, body: JSON.stringify(body ?? {}) }).then(refresh)

  const move = (delta) => {
    const ids = photos.map((p) => p.id)
    const j = index + delta
    if (j < 0 || j >= ids.length) return
    ;[ids[index], ids[j]] = [ids[j], ids[index]]
    send('PUT', `${base}/photos/order`, { media_ids: ids }).then(onClose)
  }

  return (
    <div className="fixed inset-0 z-20 flex flex-col bg-black/90 p-4 text-white" onClick={onClose}>
      <div className="flex flex-1 items-center justify-center" onClick={(e) => e.stopPropagation()}>
        {photo.status !== 'ready' ? <p>{t('photos.processing')}</p>
          : photo.kind === 'video'
            ? <video src={mediaUrl(photo.id, 'mp4')} poster={mediaUrl(photo.id, 'poster')} controls playsInline className="max-h-[70vh] max-w-full rounded-lg" />
            : <img src={mediaUrl(photo.id, 'display')} alt={photo.caption ?? ''} className="max-h-[70vh] max-w-full rounded-lg object-contain" />}
      </div>
      <div className="flex flex-col gap-2" onClick={(e) => e.stopPropagation()}>
        <input value={caption} onChange={(e) => setCaption(e.target.value)} placeholder={t('photos.caption')}
          onBlur={() => caption !== (photo.caption ?? '') && send('PATCH', `${base}/photos/${photo.id}`, { caption: caption || null })}
          className="rounded-xl bg-white/10 px-3 py-2 text-white placeholder-white/50" />
        <div className="flex justify-between text-sm">
          <button onClick={() => move(-1)} disabled={index === 0}>← {t('photos.moveLeft')}</button>
          <a href={mediaUrl(photo.id, 'original')} target="_blank" rel="noreferrer" className="underline">{t('photos.original')}</a>
          <button onClick={() => confirm(t('photos.confirmDelete')) && send('DELETE', `${base}/photos/${photo.id}`).then(onClose)} className="text-red-300">
            {t('photos.delete')}
          </button>
          <button onClick={() => move(1)} disabled={index === photos.length - 1}>{t('photos.moveRight')} →</button>
        </div>
        <button onClick={onClose} className="mt-2 rounded-full bg-white/20 py-2">{t('photos.close')}</button>
      </div>
    </div>
  )
}

// Gallery for any owner: base = '/dates/7' or '/recipes/3'; queryKey = the owner's detail query to refresh.
export default function Photos({ base, queryKey, photos }) {
  const { t } = useT()
  const [open, setOpen] = useState(null)

  return (
    <section className="flex flex-col gap-3">
      <Uploader base={base} queryKey={queryKey} />
      <div className="grid grid-cols-3 gap-1">
        {photos.map((p, i) => (
          <button key={p.id} onClick={() => setOpen(i)} className="relative aspect-square overflow-hidden rounded-lg bg-rose-100">
            {p.status === 'ready'
              ? <img src={mediaUrl(p.id, 'thumb')} alt={p.caption ?? ''} loading="lazy" className="h-full w-full object-cover" />
              : <span className="text-xs text-rose-400">{t(p.status === 'failed' ? 'photos.failed' : 'photos.processing')}</span>}
            {p.kind === 'video' && (
              <span className="absolute bottom-1 right-1 rounded bg-black/60 px-1 text-xs text-white">
                ▶ {p.duration_s ? `${Math.floor(p.duration_s / 60)}:${String(Math.round(p.duration_s % 60)).padStart(2, '0')}` : ''}
              </span>
            )}
          </button>
        ))}
      </div>
      {open != null && photos[open] && <Lightbox key={photos[open].id} base={base} queryKey={queryKey} photos={photos} index={open} onClose={() => setOpen(null)} />}
    </section>
  )
}
