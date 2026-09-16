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
