export interface OrchestratorEvent {
	run_id: string;
	repo: string;
	node: string;
	provider: string;
	status: 'success' | 'failed' | 'blocked';
	detail?: string;
	pr_url?: string;
	created_at?: string;
}

export interface RunGroup {
	runId: string;
	repo: string;
	nodes: Record<string, OrchestratorEvent>;
}

export type ConnectionStatus = 'connecting' | 'open' | 'closed';
