import { Link, useSearchParams } from 'react-router-dom'
import { mediaUrl } from '../components/Photos.jsx'
import { TagChips } from '../components/Tags.jsx'
import { useT } from '../i18n/index.jsx'
import { useRecipes } from '../recipes.js'

export default function Recipes() {
  const { t } = useT()
  const [params, setParams] = useSearchParams()
  const status = params.get('status') === 'cooked' ? 'cooked' : 'want'
  const { data: recipes = [], isLoading } = useRecipes(status)

  return (
    <main className="min-h-[85vh] bg-rose-50 p-4 font-sans text-rose-900">
      <div className="mx-auto flex max-w-md flex-col gap-3">
        <h1 className="font-display text-3xl italic text-rose-600">{t('recipes.title')}</h1>
        <div className="flex gap-2">
          {['want', 'cooked'].map((s) => (
            <button key={s} onClick={() => setParams({ status: s }, { replace: true })}
              className={`rounded-full px-4 py-2 text-sm font-bold ${status === s ? 'bg-rose-500 text-white' : 'bg-white'}`}>
              {t(`recipes.status.${s}`)}
            </button>
          ))}
        </div>
        {!isLoading && recipes.length === 0 && <p className="py-10 text-center text-sm">{t('recipes.empty')}</p>}
        {recipes.map((r) => (
          <Link key={r.id} to={`/recipes/${r.id}`} className="flex gap-3 rounded-2xl bg-white p-3 shadow-sm active:scale-[0.99]">
            <div className="h-16 w-16 shrink-0 overflow-hidden rounded-xl bg-rose-100">
              {r.thumb_id ? <img src={mediaUrl(r.thumb_id, 'thumb')} alt="" className="h-full w-full object-cover" /> : <span className="flex h-full items-center justify-center text-2xl">🍲</span>}
            </div>
            <div className="flex min-w-0 flex-col gap-1">
              <span className="truncate font-bold">{r.title}</span>
              <span className="text-xs text-rose-400">
                {r.prep_minutes != null && `⏱ ${r.prep_minutes} min · `}{t('recipes.portions', { count: r.portions })}
              </span>
              {r.tags.length > 0 && <TagChips tags={r.tags} />}
            </div>
          </Link>
        ))}
      </div>
      <Link to="/recipes/new" aria-label={t('recipes.new')}
        className="fixed bottom-6 right-6 flex h-14 w-14 items-center justify-center rounded-full bg-rose-500 text-3xl text-white shadow-lg active:scale-95">
        +
      </Link>
    </main>
  )
}
