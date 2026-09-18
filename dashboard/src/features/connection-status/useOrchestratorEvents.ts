import { useEffect, useRef, useState } from 'react'
import type { ConnectionStatus, OrchestratorEvent } from '../../types/orchestrator'


const WS_URL = import.meta.env.VITE_ORCHESTRATOR_API_URL.replace(/^http/, 'ws') + '/ws'

const BASE_RECONNECT_DELAY_MS = 1_000
const MAX_RECONNECT_DELAY_MS = 30_000

export function useOrchestratorEvents() {
  const [events, setEvents] = useState<OrchestratorEvent[]>([])
  const [status, setStatus] = useState<ConnectionStatus>('connecting')


  const socketRef = useRef<WebSocket | null>(null)
  const attemptRef = useRef(0)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const unmountedRef = useRef(false)

  useEffect(() => {
    unmountedRef.current = false

    function connect() {
      const ws = new WebSocket(WS_URL)
      socketRef.current = ws
      setStatus('connecting')

      ws.onopen = () => {
        attemptRef.current = 0
        setStatus('open')
      }

      ws.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data) as OrchestratorEvent
          setEvents((prev) => [...prev, parsed])
        } catch {
          console.error('Parsing error:', event.data)
        }
      }

      ws.onerror = () => {
        ws.close()
      }

      ws.onclose = () => {
        if(socketRef.current !== null) return
        socketRef.current = null
        setStatus('closed')
        if (unmountedRef.current) return

        const delay = Math.min(
          BASE_RECONNECT_DELAY_MS * 2 ** attemptRef.current,
          MAX_RECONNECT_DELAY_MS,
        )
        attemptRef.current += 1
        reconnectTimerRef.current = setTimeout(connect, delay)
      }
    }

    connect()

    return () => {
      unmountedRef.current = true
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current)
      socketRef.current?.close()
    }
  }, [])

  return { events, status }
}