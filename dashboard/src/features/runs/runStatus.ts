import type { RunGroup } from "../../types/orchestrator";


export function isRunComplete(run: RunGroup, prStatus?: string): boolean {
	return !!run.nodes.manually_completed || !!run.nodes.pr_merged || prStatus === 'merged';
}
