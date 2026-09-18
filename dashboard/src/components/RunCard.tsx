import { useEffect, useState, type KeyboardEvent } from 'react';
import type { RunGroup } from '../types/orchestrator';
import { Button, Card, Link, Spinner, StatusBadge } from '@szczypkaweb/shared-ui';
import { nodeLabel, toBadgeStatus } from '../lib/nodeLabels';
import RunDetailsModal from './RunDetailsModal';

// How long a non-finished run can go without any new event before we stop
// showing "Working..." and instead flag it as possibly interrupted (e.g. the
// backend process died/restarted mid-run). Generous on purpose - the writer
// node does real agentic coding work and can legitimately run for many
// minutes with no event in between (we only get a "node finished" event,
// never "node started", so a long writer step looks identical to a dead one
// until either it finishes or this timeout is reached). Bumped from 15 to 30
// minutes after seeing a false positive on a real, still-running writer
// step. Tune up further if you still see false positives, or down if stuck
// runs take too long to be flagged.
const STALE_AFTER_MS = 30 * 60 * 1000;

interface RunCardProps {
	run: RunGroup;
	// PR status and completion are computed once in App.tsx (via useQueries)
	// so the Active/History split can see them too - see lib/runStatus.ts.
	// RunCard just renders what it's given rather than re-fetching.
	prStatus?: string;
	prStatusLoading?: boolean;
	isComplete: boolean;
	compact?: boolean;
	// Only relevant to stale, still-active runs - lets the user manually move
	// one to History when its backend process died and it'll never send
	// another event. This hits a real backend endpoint (POST
	// /runs/complete, see api/runs.ts's completeRun) rather than just
	// flipping client-side state, so it's still marked done after a refresh.
	// Omitted entirely for compact (already-done) cards, since they have
	// nothing left to end.
	onMarkComplete?: () => void;
	markCompletePending?: boolean;
}

export default function RunCard({
	run,
	prStatus,
	prStatusLoading,
	isComplete,
	compact = false,
	onMarkComplete,
	markCompletePending = false,
}: RunCardProps) {
	const [detailsOpen, setDetailsOpen] = useState(false);
	const prUrl = run.nodes.writer?.pr_url;

	// Force a re-check every 30s even if no new event arrives - otherwise a
	// run that goes silent (e.g. the backend crashed) would only ever be
	// re-evaluated the next time *something else* causes this component to
	// re-render, which might be never if nothing else is happening either.
	const [, tick] = useState(0);
	useEffect(() => {
		const interval = setInterval(() => tick((t) => t + 1), 30_000);
		return () => clearInterval(interval);
	}, []);

	const lastEventAt = Math.max(
		0,
		...Object.values(run.nodes).map((event) => (event.created_at ? new Date(event.created_at).getTime() : 0))
	);
	const isStale = !isComplete && lastEventAt > 0 && Date.now() - lastEventAt > STALE_AFTER_MS;

	// The whole card opens the run-details modal (task description, full
	// status breakdown, PR link, token/cost telemetry) - replaces the old
	// inline "Task description" accordion. Interactive children (PR link,
	// "Mark as done" button) stop propagation so clicking them doesn't also
	// pop the modal open.
	function handleCardKeyDown(event: KeyboardEvent<HTMLDivElement>) {
		if (event.key === 'Enter' || event.key === ' ') {
			event.preventDefault();
			setDetailsOpen(true);
		}
	}

	const cardBody = (
		<>
			<div className="flex items-center justify-between gap-2">
				<p className="text-sm text-muted-foreground">
					{run.repo} · {run.runId.slice(0, 8)}
				</p>
				{compact && <StatusBadge status="done" />}
			</div>

			{prUrl && (
				<div className="mt-2 flex items-center gap-2">
					<Link
						href={prUrl}
						external
						className={compact ? 'text-xs' : 'text-sm'}
						onClick={(event) => event.stopPropagation()}>
						{compact ? 'PR' : 'View PR'}
					</Link>
					{!compact && prStatusLoading && <Spinner size="small" label="Checking PR status..." />}
					{prStatus && <span className="text-xs text-muted-foreground">({prStatus})</span>}
				</div>
			)}

			{!compact && (
				<div className="mt-2 flex flex-wrap items-center gap-2">
					{Object.entries(run.nodes)
						.filter(([node]) => node !== 'trigger')
						.map(([node, event]) => (
							<div
								key={node}
								className="flex items-center gap-1.5">
								<span className="text-sm">{nodeLabel(node)}</span>
								<StatusBadge status={toBadgeStatus(event.status)} />
							</div>
						))}
					{!isComplete && (
						<div className="flex items-center gap-1.5">
							{isStale ? (
								<>
									<span className="text-sm text-amber-600">
										⚠ No update in a while - may have been interrupted
									</span>
									{onMarkComplete && (
										<Button
											type="button"
											variant="secondary"
											size="small"
											disabled={markCompletePending}
											onClick={(event) => {
												event.stopPropagation();
												onMarkComplete();
											}}>
											{markCompletePending ? 'Marking as done...' : 'Mark as done'}
										</Button>
									)}
								</>
							) : (
								<>
									<Spinner size="small" label="Working..." />
									<span className="text-sm text-muted-foreground">Working...</span>
								</>
							)}
						</div>
					)}
				</div>
			)}
		</>
	);

	return (
		<>
			<Card
				padding="compact"
				role="button"
				tabIndex={0}
				onClick={() => setDetailsOpen(true)}
				onKeyDown={handleCardKeyDown}
				className="cursor-pointer transition-colors hover:bg-muted/50">
				{cardBody}
			</Card>
			<RunDetailsModal
				run={run}
				open={detailsOpen}
				onOpenChange={setDetailsOpen}
				prStatus={prStatus}
			/>
		</>
	);
}
