import { describe, expect, it } from 'vitest'
import { translate } from '../i18n'

describe('appliance hazard warnings', () => {
  it('are shown in Hindi when the interface is Hindi', () => {
    expect(translate('Hindi', 'hazard.mwTitle')).toContain('माइक्रोवेव')
    expect(translate('Hindi', 'hazard.chatMwTitle')).toContain('माइक्रोवेव')
    expect(translate('Hindi', 'hazard.solarTitle')).toContain('सोलर')
  })
  it('fall back to English for other languages', () => {
    expect(translate('Kannada', 'hazard.mwTitle')).toBe('Microwave: switching off the MCB is not enough')
    expect(translate('English', 'hazard.chatMwText')).toContain('high-voltage capacitor')
  })
})
