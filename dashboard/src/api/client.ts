const API_URL = import.meta.env.VITE_ORCHESTRATOR_API_URL;

if (!API_URL) {
  throw new Error(
    "VITE_ORCHESTRATOR_API_URL is not set - copy .env.example to .env and adjust it."
  );
}

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...init,
    });
  } catch {
    throw new ApiError(0, `Could not reach the orchestrator API at ${API_URL}`);
  }

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new ApiError(res.status, body || `${path} failed with status ${res.status}`);
  }

  return (await res.json()) as T;
}
