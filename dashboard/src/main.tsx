import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import './index.css'
import App from './App.tsx'

// shared-ui's design tokens only switch to their dark variants when a `.dark`
// class is present on an ancestor (see its globals.css `@custom-variant
// dark`) - this app previously had no mechanism at all for adding that
// class, so every shared-ui component (SidePanel, Card, ...) always
// rendered in light mode regardless of the OS theme. Mirror the OS
// preference onto <html> here, and keep it in sync if the user changes
// their system theme while the app is open.
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
