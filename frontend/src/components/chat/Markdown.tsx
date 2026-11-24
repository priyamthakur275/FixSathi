import { Fragment } from 'react'
import type { SourceRef } from '../../types'
import { parseBlocks, type Inline } from '../../utils/text'

/** Renders the light Markdown the assistant uses. Builds React elements only, so no model text is ever injected as HTML. */
export function Markdown({ text, sources = [] }: { text: string; sources?: SourceRef[] }) {
  const index = new Map(sources.map((s, i) => [s.record_id, i + 1]))
  const inl = (items: Inline[]) => items.map((x, i) => {
    if (x.t === 'bold') return <strong key={i}>{x.v}</strong>
    if (x.t === 'italic') return <em key={i}>{x.v}</em>
    if (x.t === 'code') return <code key={i}>{x.v}</code>
    if (x.t === 'cite') {
      const n = index.get(x.v)
      const src = sources.find(s => s.record_id === x.v)
      return n ? <span key={i} title={src ? `${src.source_name} (${x.v})` : x.v} className="relative -top-0.5 mx-0.5 inline-flex h-[17px] min-w-[17px] items-center justify-center rounded-full bg-teal/15 px-1 align-middle text-[10px] font-semibold leading-none text-teal">{n}</span> : null
    }
    return <Fragment key={i}>{x.v}</Fragment>
  })
  return (
    <div className="md">
      {parseBlocks(text).map((b, i) => {
        if (b.t === 'p') return <p key={i}>{inl(b.inl)}</p>
        if (b.t === 'ul') return <ul key={i}>{b.items.map((it, j) => <li key={j}>{inl(it)}</li>)}</ul>
        return <ol key={i} start={b.start}>{b.items.map((it, j) => <li key={j}>{inl(it)}</li>)}</ol>
      })}
    </div>
  )
}
