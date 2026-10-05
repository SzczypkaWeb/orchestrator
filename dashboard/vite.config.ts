import path from 'node:path'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  // tailwindcss is a plugin FACTORY - it must be called. Passing the bare
  // reference silently produces no working Tailwind plugin (no build error,
  // just none of the utility classes ever actually get generated).
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': path.resolve(import.meta.dirname, 'src') } },
})
