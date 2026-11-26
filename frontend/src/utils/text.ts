/** Text helpers shared by chat rendering and voice. */

export const CITATION = /\[([a-z]+:[^\]\s]{1,110})\]/g

/** Plain text for speech synthesis: no Markdown symbols, no record ids. */
export function speakable(s: string): string {
  return s
    .replace(CITATION, '')
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/(?<![\w*])\*(?!\s)([^*\n]+?)\*(?![\w*])/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/^\s*#{1,6}\s+/gm, '')
    .replace(/^\s*[-*•]\s+/gm, '')
    .replace(/^\s*(\d+)[.)]\s+/gm, '$1. ')
    .replace(/[ \t]+([.,;:!?)])/g, '$1')
    .replace(/[ \t]{2,}/g, ' ')
    .trim()
}

export type Inline = { t: 'text' | 'bold' | 'italic' | 'code' | 'cite'; v: string }
export type Block = { t: 'p'; inl: Inline[] } | { t: 'ul' | 'ol'; items: Inline[][]; start?: number }

/** Inline Markdown: **bold**, *italic*, `code`, [record:id] citations. Everything else stays literal text. */
export function parseInline(s: string): Inline[] {
  const out: Inline[] = []
  const re = /\*\*(.+?)\*\*|`([^`]+)`|\[([a-z]+:[^\]\s]{1,110})\]|(?<![\w*])\*(?!\s)([^*\n]+?)\*(?![\w*])/g
  let last = 0
  for (let m = re.exec(s); m; m = re.exec(s)) {
    if (m.index > last) out.push({ t: 'text', v: s.slice(last, m.index) })
    if (m[1] !== undefined) out.push({ t: 'bold', v: m[1] })
    else if (m[2] !== undefined) out.push({ t: 'code', v: m[2] })
    else if (m[3] !== undefined) out.push({ t: 'cite', v: m[3] })
    else out.push({ t: 'italic', v: m[4] })
    last = re.lastIndex
  }
  if (last < s.length) out.push({ t: 'text', v: s.slice(last) })
  return out
}

/** Block Markdown: paragraphs, '-'/'*' bullets, '1.' lists. Headings become bold paragraphs. Safe: produces data, never HTML. */
export function parseBlocks(src: string): Block[] {
  const blocks: Block[] = []
  let para: string[] = []
  const flush = () => { if (para.length) { blocks.push({ t: 'p', inl: parseInline(para.join(' ')) }); para = [] } }
  for (const raw of src.replace(/\r/g, '').split('\n')) {
    const line = raw.trimEnd()
    const ul = /^\s*[-*•]\s+(.*)$/.exec(line)
    const ol = /^\s*(\d+)[.)]\s+(.*)$/.exec(line)
    const h = /^\s*#{1,6}\s+(.*)$/.exec(line)
    if (!line.trim()) { flush(); continue }
    if (ul || ol) {
      flush()
      const kind = ul ? 'ul' : 'ol'
      const text = ul ? ul[1] : ol![2]
      const prev = blocks[blocks.length - 1]
      if (prev && prev.t === kind) prev.items.push(parseInline(text))
      else blocks.push(kind === 'ol' ? { t: 'ol', items: [parseInline(text)], start: Number(ol![1]) } : { t: 'ul', items: [parseInline(text)] })
      continue
    }
    if (h) { flush(); blocks.push({ t: 'p', inl: [{ t: 'bold', v: h[1].replace(/\*\*/g, '') }] }); continue }
    const prev = blocks[blocks.length - 1]
    if (!para.length && prev && prev.t !== 'p' && /^\s{2,}\S/.test(raw)) {  // indented continuation of a list item
      prev.items[prev.items.length - 1].push({ t: 'text', v: ' ' }, ...parseInline(line.trim())); continue
    }
    para.push(line.trim())
  }
  flush()
  return blocks
}
