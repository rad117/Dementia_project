import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [tailwindcss(), react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.js'],
    globals: true,
    // shortcut: default pools fail with "Cannot read properties of undefined (reading 'config')" on vitest 5.0.2 here; revisit on upgrade.
    pool: 'vmThreads',
  },
})
