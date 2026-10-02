import { describe, expect, it } from 'vitest'
import { translate } from './translate.js'

const dict = {
  hello: 'Živjo, {name}!',
  dates: { one: '{count} zmenek', two: '{count} zmenka', few: '{count} zmenki', other: '{count} zmenkov' },
}

describe('translate', () => {
  it('interpolates variables', () => {
    expect(translate('sl', dict, 'hello', { name: 'Ana' })).toBe('Živjo, Ana!')
  })

  it('uses Slovenian plural forms one/two/few/other', () => {
    expect([1, 2, 3, 4, 5, 101, 102].map((count) => translate('sl', dict, 'dates', { count }))).toEqual([
      '1 zmenek', '2 zmenka', '3 zmenki', '4 zmenki', '5 zmenkov', '101 zmenek', '102 zmenka',
    ])
  })

  it('falls back to the key when missing', () => {
    expect(translate('sl', dict, 'nope.missing')).toBe('nope.missing')
  })
})
