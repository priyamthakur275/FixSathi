import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App'
import { apiBase } from './services/api'

// The theme is applied before paint by index.html and kept in sync by PrefsContext.
// Wake the free-tier API as soon as the page opens, so it is warm by the time the person taps anything.
void fetch(`${apiBase}/health`, { mode: 'no-cors', cache: 'no-store' }).catch(() => undefined)

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>)
