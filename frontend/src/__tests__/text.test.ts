import { describe, expect, it } from 'vitest'
import { parseBlocks, parseInline, speakable } from '../utils/text'

describe('chat markdown', () => {
  it('parses paragraphs, bullets and numbered steps', () => {
    const b = parseBlocks('Likely a capacitor.\n\n- **Capacitor** weak\n- Bearings\n\n1. Switch off\n2. Test')
    expect(b.map(x => x.t)).toEqual(['p', 'ul', 'ol'])
    expect(b[1].t === 'ul' && b[1].items.length).toBe(2)
    expect(b[2].t === 'ol' && b[2].start).toBe(1)
  })
  it('keeps model text as data: no HTML is interpreted', () => {
    const b = parseBlocks('<img src=x onerror=alert(1)>')
    expect(b[0].t === 'p' && b[0].inl[0]).toEqual({ t: 'text', v: '<img src=x onerror=alert(1)>' })
  })
  it('extracts bold, code and record citations', () => {
    expect(parseInline('Check **MCB** then `CH38` [mfr:lg-ac-ch38].').map(x => x.t)).toEqual(['text', 'bold', 'text', 'code', 'text', 'cite', 'text'])
  })
  it('turns headings into bold paragraphs', () => {
    const b = parseBlocks('### Next steps')
    expect(b[0].t === 'p' && b[0].inl[0]).toEqual({ t: 'bold', v: 'Next steps' })
  })
})

describe('speakable', () => {
  it('removes markdown symbols and citations for speech', () => {
    expect(speakable('**Switch off** the MCB [mfr:x-1].\n- Then test')).toBe('Switch off the MCB.\nThen test')
  })
})

describe('italic', () => {
  it('renders *italic* without touching bullets or multiplication', async () => {
    const { parseInline, speakable } = await import('../utils/text')
    expect(parseInline('*(power-sensitive step withheld)*')).toEqual([{ t: 'italic', v: '(power-sensitive step withheld)' }])
    expect(parseInline('2*3 and 4*5').every(x => x.t === 'text')).toBe(true)
    expect(speakable('*(step withheld)* now')).toBe('(step withheld) now')
  })
})
