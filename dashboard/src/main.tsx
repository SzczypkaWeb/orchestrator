import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import './index.css'
import App from './App.tsx'

// The design tokens in index.css switch to their dark values only when a `.dark`
// class is present on <html> (`@custom-variant dark`). Mirror the OS preference
// onto it, and keep it in sync if the user changes their system theme.
const darkMediaQuery = window.matchMedia('(prefers-color-scheme: dark)')

function applyDarkClass(isDark: boolean) {
	document.documentElement.classList.toggle('dark', isDark)
}

applyDarkClass(darkMediaQuery.matches)
darkMediaQuery.addEventListener('change', (event) => applyDarkClass(event.matches))

const queryClient = new QueryClient()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
)
