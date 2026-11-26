// Test runner settings (kept apart from vite.config.ts, which the production build typechecks).
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react() as never],
  test: { environment: 'jsdom', setupFiles: ['./src/__tests__/setup.ts'], include: ['src/**/*.test.{ts,tsx}'] },
})
