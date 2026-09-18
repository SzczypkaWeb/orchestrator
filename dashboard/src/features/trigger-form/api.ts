import { apiFetch } from "../../api/client";


export interface ReposResponse {
  repos: string[];
}

export function fetchRepos(): Promise<ReposResponse> {
  return apiFetch<ReposResponse>("/repos");
}
