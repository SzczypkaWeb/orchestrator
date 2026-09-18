import type { OrchestratorEvent } from "../types/orchestrator";
import { apiFetch } from "./client";

export interface TriggerRunInput {
  task: string;
  repo?: string;
}

export interface TriggerRunResponse {
  status: string;
  task: string;
  repo: string | null;
}

export function triggerRun(input: TriggerRunInput): Promise<TriggerRunResponse> {
  return apiFetch<TriggerRunResponse>("/runs", {
    method: "POST",
    body: JSON.stringify(input),
  });
}


export function fetchRunHistory(): Promise<{ events: OrchestratorEvent[] }> {
  return apiFetch<{ events: OrchestratorEvent[] }>('/runs')
}

export function fetchPrStatus(url: string): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/pr-status?url=${encodeURIComponent(url)}`);
}

export interface RunMetric {
  node: string;
  provider: string;
  model: string;
  inputTokens: number | null;
  outputTokens: number | null;
  totalCostUsd: number | null;
  durationMs: number;
  success: boolean;
  errorMessage: string | null;
  createdAt: string;
}

interface RunMetricResponse {
  node: string;
  provider: string;
  model: string;
  input_tokens: number | null;
  output_tokens: number | null;
  total_cost_usd: number | null;
  duration_ms: number;
  success: boolean;
  error_message: string | null;
  created_at: string;
}

// Token/cost/duration telemetry for one run - see orchestrator/telemetry.py's
// record_metric (already written on every provider call) and fetch_run_metrics
// (new - this data was being recorded all along but never surfaced in the UI
// until the run-details modal). Mapped from the API's snake_case shape to
// camelCase here, same as the rest of this file's response handling.
export async function fetchRunMetrics(runId: string): Promise<RunMetric[]> {
  const { metrics } = await apiFetch<{ metrics: RunMetricResponse[] }>(
    `/runs/${encodeURIComponent(runId)}/metrics`
  );
  return metrics.map((m) => ({
    node: m.node,
    provider: m.provider,
    model: m.model,
    inputTokens: m.input_tokens,
    outputTokens: m.output_tokens,
    totalCostUsd: m.total_cost_usd,
    durationMs: m.duration_ms,
    success: m.success,
    errorMessage: m.error_message,
    createdAt: m.created_at,
  }));
}

export interface CompleteRunInput {
  runId: string;
  repo: string;
}

// Manually ends a run that will never finish on its own (backend process
// died mid-run, no more events coming). This is a real persisted RunEvent
// (see control_server.py's /runs/complete), not just client-side state - so
// it survives a refresh and shows up the same way for anyone else looking
// at this dashboard.
export function completeRun(input: CompleteRunInput): Promise<{ status: string }> {
  return apiFetch<{ status: string }>('/runs/complete', {
    method: 'POST',
    body: JSON.stringify({ run_id: input.runId, repo: input.repo }),
  });
}

export interface RecordPrMergedInput {
  runId: string;
  repo: string;
  prUrl: string;
}

// System-detected (not user-clicked) completion signal: called once, the
// first time a run's live PR-status check comes back "merged", so that fact
// gets persisted as a real RunEvent (control_server.py's /runs/pr-merged)
// instead of needing to re-ask GitHub on every future page load. Without
// this, a merged run flashes into the Active section on every refresh until
// the live check resolves again - see App.tsx's usage for the one-shot guard.
export function recordPrMerged(input: RecordPrMergedInput): Promise<{ status: string }> {
  return apiFetch<{ status: string }>('/runs/pr-merged', {
    method: 'POST',
    body: JSON.stringify({ run_id: input.runId, repo: input.repo, pr_url: input.prUrl }),
  });
}