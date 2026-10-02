// Pure lookup: dotted key → string; plural entries are {one, two, few, other} picked by Intl.PluralRules(vars.count).
export function translate(locale, dict, key, vars = {}) {
  let entry = key.split('.').reduce((node, part) => node?.[part], dict)
  if (entry && typeof entry === 'object' && 'count' in vars) {
    entry = entry[new Intl.PluralRules(locale).select(vars.count)] ?? entry.other
  }
  if (typeof entry !== 'string') return key
  return entry.replace(/\{(\w+)\}/g, (m, name) => (name in vars ? vars[name] : m))
}
