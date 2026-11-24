import { mediaUrl } from '../services/api'
import type { MessageFile } from '../types'

const VIEWABLE = /\.(pdf|txt|csv|md|log)$/i

/** Opens an attached file. Server files need the login token, so they are fetched first and shown from a temporary local URL.
 *  PDFs and text open in a new tab; Word files download. The tab is opened right away so pop-up blockers allow it. */
export async function openFile(f: MessageFile): Promise<void> {
  const name = f.name || 'document'
  const view = (f.mime ? /pdf|^text\//.test(f.mime) : VIEWABLE.test(name))
  if (!f.server) {
    if (view) window.open(f.url, '_blank', 'noopener'); else download(f.url, name)
    return
  }
  const tab = view ? window.open('', '_blank') : null
  try {
    const url = await mediaUrl(f.url)
    if (tab) tab.location.href = url
    else download(url, name)
    setTimeout(() => URL.revokeObjectURL(url), 60_000)
  } catch (e) {
    tab?.close()
    throw e
  }
}

function download(url: string, name: string) {
  const a = document.createElement('a'); a.href = url; a.download = name; a.rel = 'noopener'
  document.body.appendChild(a); a.click(); a.remove()
}
