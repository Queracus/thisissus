import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api.js'
import { useT } from '../i18n/index.jsx'
import { useSpaces } from '../spaces.jsx'

export function useTags() {
  const { active } = useSpaces()
  return useQuery({ queryKey: ['tags', active?.id], queryFn: () => api('/tags'), enabled: !!active })
}

export function useTagLabel() {
  const { t } = useT()
  return (tag) => (tag.starter_key ? t(`tags.starter.${tag.starter_key}`) : tag.name)
}

export function TagChips({ tags }) {
  const label = useTagLabel()
  return (
    <span className="flex flex-wrap gap-1">
      {tags.map((tag) => <span key={tag.id} className="rounded-full bg-rose-100 px-2 py-0.5 text-xs">{label(tag)}</span>)}
    </span>
  )
}

// Toggle existing tags; typing a new name + Enter creates it (or reuses one with the same name).
export function TagPicker({ value, onChange, allowCreate = true }) {
  const { t } = useT()
  const label = useTagLabel()
  const qc = useQueryClient()
  const { data: tags = [] } = useTags()
  const [draft, setDraft] = useState('')
  // onChange is a state setter: functional updates stay correct even for rapid taps.
  const toggle = (id) => onChange((cur) => (cur.includes(id) ? cur.filter((v) => v !== id) : [...cur, id]))

  async function create(e) {
    if (e.key !== 'Enter' || !draft.trim()) return
    e.preventDefault()
    const tag = await api('/tags', { method: 'POST', body: JSON.stringify({ name: draft.trim() }) })
    qc.invalidateQueries({ queryKey: ['tags'] })
    onChange((cur) => (cur.includes(tag.id) ? cur : [...cur, tag.id]))
    setDraft('')
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap gap-2">
        {tags.map((tag) => (
          <button key={tag.id} type="button" onClick={() => toggle(tag.id)}
            className={`rounded-full px-3 py-1 text-sm ${value.includes(tag.id) ? 'bg-rose-500 text-white' : 'bg-white'}`}>
            {label(tag)}
          </button>
        ))}
      </div>
      {allowCreate && (
        <input value={draft} onChange={(e) => setDraft(e.target.value)} onKeyDown={create} placeholder={t('tags.newPlaceholder')}
          className="rounded-xl border border-rose-200 bg-white px-4 py-2 text-sm outline-rose-400" />
      )}
    </div>
  )
}
