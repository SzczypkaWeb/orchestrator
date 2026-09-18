import type { OrchestratorEvent } from '../types/orchestrator';
import type { StatusBadgeStatus } from '@szczypkaweb/shared-ui';

// Shared between RunCard (inline per-node badges on the full/active card)
// and RunDetailsModal (full node-by-node breakdown for any run, including
// compact/history ones that don't show it inline) - kept in one place so the
// two views can't drift out of sync on labels/status mapping.
export const NODE_LABELS: Record<string, string> = {
	trigger: 'Task submitted',
	classify_task: 'Classifying task',
	writer: 'Writing code',
	verify: 'Verifying (tests/build)',
	security_review: 'Security review',
	manually_completed: 'Manually marked as done',
	pr_merged: 'PR merged',
};

export function nodeLabel(node: string): string {
	return NODE_LABELS[node] ?? node;
}

export function toBadgeStatus(status: OrchestratorEvent['status']): StatusBadgeStatus {
	if (status === 'success') return 'done';
	return status;
}
