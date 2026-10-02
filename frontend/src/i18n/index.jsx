import { createContext, useContext, useEffect, useMemo } from 'react'
import { useMe } from '../auth.js'
import en from './en.json'
import sl from './sl.json'
import { translate } from './translate.js'

const dicts = { sl, en }
export const LOCALES = ['sl', 'en']
const I18n = createContext(null)

const browserLocale = () => ((navigator.language || '').toLowerCase().startsWith('sl') ? 'sl' : 'en')

// Locale comes from the logged-in user; before login, from the browser.
export function I18nProvider({ children }) {
  const { data: me } = useMe()
  const locale = me?.locale ?? browserLocale()
  useEffect(() => { document.documentElement.lang = locale }, [locale])

  const value = useMemo(() => {
    const t = (key, vars) => translate(locale, dicts[locale], key, vars)
    // API error → message: error.<code>, else the generic one.
    const tError = (e) => {
      const key = `error.${e.code}`
      const msg = t(key, { minutes: Math.ceil((e.body?.retry_after ?? 0) / 60) })
      return msg === key ? t('error.generic', { code: e.code || e.name }) : msg
    }
    return { t, tError, locale }
  }, [locale])

  return <I18n.Provider value={value}>{children}</I18n.Provider>
}

export const useT = () => useContext(I18n)
