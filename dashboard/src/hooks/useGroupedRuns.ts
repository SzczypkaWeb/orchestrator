import { useMemo } from 'react'
import type { OrchestratorEvent, RunGroup } from '../types/orchestrator'

export function useGroupedRuns(events: OrchestratorEvent[]): RunGroup[] {
  return useMemo(() => {
    const byRunId = new Map<string, RunGroup>()

    for (const event of events) {
      let group = byRunId.get(event.run_id)
      if (!group) {
        group = { runId: event.run_id, repo: event.repo, nodes: {} }
        byRunId.set(event.run_id, group)
      }
      group.nodes[event.node] = event
    }

    return Array.from(byRunId.values())
  }, [events])
}