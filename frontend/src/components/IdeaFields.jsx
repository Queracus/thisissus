import { SEASONS, SEASON_EMOJI } from '../ideas.js'
import { useT } from '../i18n/index.jsx'
import { TagPicker } from './Tags.jsx'

const field = 'w-full rounded-xl border border-rose-200 bg-white px-4 py-3 text-left outline-rose-400'

export const emptyIdea = { title: '', description: '', url: '', est_cost: '', season: null, tag_ids: [] }

export const ideaToForm = (idea) => ({
  title: idea.title, description: idea.description ?? '', url: idea.url ?? '', est_cost: idea.est_cost ?? '',
  season: idea.season, tag_ids: idea.tags.map((t) => t.id),
})

export const formToBody = (v) => ({
  title: v.title, description: v.description || null, url: v.url || null,
  est_cost: v.est_cost === '' ? null : Number(v.est_cost), season: v.season, tag_ids: v.tag_ids,
})

// Details shared by the new-idea flow and the edit page.
export default function IdeaFields({ value, onChange, withTitle = true }) {
  const { t } = useT()
  // onChange is a state setter; functional updates never overwrite a change made a moment earlier.
  const set = (k) => (e) => { const v = e.target.value; onChange((cur) => ({ ...cur, [k]: v })) }

  return (
    <div className="flex w-full flex-col gap-3 text-sm">
      {withTitle && <label>{t('ideas.field.title')}<input required className={field} value={value.title} onChange={set('title')} /></label>}
      <label>{t('ideas.field.description')}<textarea rows={3} className={field} value={value.description} onChange={set('description')} /></label>
      <label>{t('ideas.field.url')}<input type="url" placeholder="https://" className={field} value={value.url} onChange={set('url')} /></label>
      <label>{t('ideas.field.est_cost')}<input type="number" min="0" step="0.01" inputMode="decimal" className={field} value={value.est_cost} onChange={set('est_cost')} /></label>
      <div className="flex flex-wrap items-center gap-2">
        {t('ideas.field.season')}:
        {SEASONS.map((s) => (
          <button key={s} type="button" onClick={() => onChange((cur) => ({ ...cur, season: cur.season === s ? null : s }))}
            className={`rounded-full px-3 py-1 ${value.season === s ? 'bg-rose-500 text-white' : 'bg-white'}`}>
            {SEASON_EMOJI[s]} {t(`ideas.season.${s}`)}
          </button>
        ))}
      </div>
      <div>{t('tags.title')}<TagPicker value={value.tag_ids} onChange={(fn) => onChange((cur) => ({ ...cur, tag_ids: typeof fn === 'function' ? fn(cur.tag_ids) : fn }))} /></div>
    </div>
  )
}
