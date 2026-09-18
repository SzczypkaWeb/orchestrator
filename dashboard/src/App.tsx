import './App.css';
import { useMutation, useQueries, useQuery } from '@tanstack/react-query';
import {
	SidePanel,
	Spinner,
} from '@szczypkaweb/shared-ui';
import { completeRun, fetchPrStatus, fetchRunHistory, recordPrMerged } from './api/runs';
import { useGroupedRuns } from './hooks/useGroupedRuns';
import { isRunComplete } from './lib/runStatus';

import { useEffect, useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import RunCard from './components/RunCard';
import { useOrchestratorEvents } from './features/connection-status/useOrchestratorEvents';
import ConnectionStatusBanner from './features/connection-status/ConnectionStatusBanner';
import TriggerForm from './features/trigger-form/TriggerForm';

function App() {
	const { data: history, isLoading: historyLoading } = useQuery({
		queryKey: ['runHistory'],
		queryFn: fetchRunHistory,
	});

	const { status, events } = useOrchestratorEvents();
	const allEvents = [...(history?.events ?? []), ...events];
	const runs = useGroupedRuns(allEvents);

	// Manually ending a stale run is a real backend write (POST
	// /runs/complete persists a "manually_completed" RunEvent - see
	// api/runs.ts) rather than client-only state, so the run stays done
	// after a refresh instead of briefly reappearing as active until some
	// local override re-applies.
	const completeRunMutation = useMutation({ mutationFn: completeRun });

	const parentRef = useRef<HTMLDivElement>(null);
	const reversedRuns = [...runs].reverse();

	// PR status has to be known BEFORE we decide which section a run belongs
	// in (a merged PR means "done" even without a security_review event), so
	// it's fetched here rather than inside RunCard. useQueries (not useQuery
	// in a .map()) is what lets this stay a single, rules-of-hooks-safe call
	// even though the number of runs varies.
	//
	// Once a run already has a persisted `pr_merged` or `manually_completed`
	// node (i.e. isRunComplete is already true from history alone, with no
	// live prStatus needed), the query is disabled entirely - there's no
	// reason to keep asking GitHub about a PR we've already recorded as
	// merged, and re-querying it would just be the same "flash into Active
	// while waiting" problem all over again.
	const prStatusResults = useQueries({
		queries: reversedRuns.map((run) => {
			const prUrl = run.nodes.writer?.pr_url;
			const alreadyKnownComplete = isRunComplete(run);
			return {
				queryKey: ['prStatus', prUrl],
				queryFn: () => fetchPrStatus(prUrl!),
				enabled: !!prUrl && !alreadyKnownComplete,
				staleTime: 60_000,
			};
		}),
	});

	const runsWithStatus = reversedRuns.map((run, index) => ({
		run,
		prStatus: prStatusResults[index].data?.status,
		prStatusLoading: prStatusResults[index].isLoading,
		isComplete: isRunComplete(run, prStatusResults[index].data?.status),
	}));

	// The first time a live PR-status check above comes back "merged" for a
	// run that isn't already recorded as such, persist it as a real
	// "pr_merged" RunEvent - see control_server.py's /runs/pr-merged and
	// lib/runStatus.ts's comment on why. `recordedMergedRef` guards against
	// firing the mutation more than once per run per session while waiting
	// for the resulting broadcast to come back over the WebSocket and land
	// in `run.nodes.pr_merged` (at which point the query above disables
	// itself and this effect has nothing left to do for that run).
	const recordPrMergedMutation = useMutation({ mutationFn: recordPrMerged });
	const recordedMergedRef = useRef<Set<string>>(new Set());
	useEffect(() => {
		for (const { run, prStatus } of runsWithStatus) {
			const prUrl = run.nodes.writer?.pr_url;
			const alreadyRecorded = !!run.nodes.pr_merged || !!run.nodes.manually_completed;
			if (prStatus === 'merged' && prUrl && !alreadyRecorded && !recordedMergedRef.current.has(run.runId)) {
				recordedMergedRef.current.add(run.runId);
				recordPrMergedMutation.mutate({ runId: run.runId, repo: run.repo, prUrl });
			}
		}
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [runsWithStatus]);

	// A run only moves to History once its PR is actually merged (or a human
	// manually ended it) - see lib/runStatus.ts for why reaching the graph's
	// last node isn't treated as "done" on its own.
	const activeRuns = runsWithStatus.filter((r) => !r.isComplete);
	const historyRuns = runsWithStatus.filter((r) => r.isComplete);

	const virtualizer = useVirtualizer({
		count: historyRuns.length,
		getScrollElement: () => parentRef.current,
		estimateSize: () => 80, // initial guess only - measureElement (below) corrects it per-card once rendered
		overscan: 5,
	});

	return (
		<>
			<main id="center">
				<h1>Orchestrator</h1>

				<TriggerForm />

				<ConnectionStatusBanner status={status} />
			</main>

			<aside className="fixed top-4 right-4 bottom-4">
				<SidePanel className="h-full">
					{historyLoading ? (
						<div className="flex items-center justify-center gap-2 p-6">
							<Spinner size="small" />
							<span className="text-sm text-muted-foreground">
								Loading history...
							</span>
						</div>
					) : (
						<div className="flex h-full flex-col">
							{activeRuns.length > 0 && (
								<div className="flex max-h-[50%] flex-col gap-2 overflow-y-auto border-b border-border p-3">
									<p className="text-xs font-semibold uppercase text-muted-foreground">
										Active
									</p>
									{activeRuns.map(({ run, prStatus, prStatusLoading, isComplete }) => (
										<RunCard
											key={run.runId}
											run={run}
											prStatus={prStatus}
											prStatusLoading={prStatusLoading}
											isComplete={isComplete}
											onMarkComplete={() =>
												completeRunMutation.mutate({ runId: run.runId, repo: run.repo })
											}
											markCompletePending={
												completeRunMutation.isPending &&
												completeRunMutation.variables?.runId === run.runId
											}
										/>
									))}
								</div>
							)}

							<div className="flex min-h-0 flex-1 flex-col">
								<p className="px-3 pt-3 text-xs font-semibold uppercase text-muted-foreground">
									History
								</p>
								<div
									ref={parentRef}
									className="flex-1 overflow-y-auto p-3">
									<div
										style={{
											height: virtualizer.getTotalSize(),
											position: 'relative',
											width: '100%',
										}}>
										{virtualizer.getVirtualItems().map((virtualRow) => {
											const { run, prStatus, prStatusLoading, isComplete } =
												historyRuns[virtualRow.index];
											return (
												<div
													key={run.runId}
													data-index={virtualRow.index}
													ref={virtualizer.measureElement}
													style={{
														position: 'absolute',
														top: 0,
														left: 0,
														width: '100%',
														transform: `translateY(${virtualRow.start}px)`,
													}}>
													<RunCard
														run={run}
														prStatus={prStatus}
														prStatusLoading={prStatusLoading}
														isComplete={isComplete}
														compact
													/>
												</div>
											);
										})}
									</div>
								</div>
							</div>
						</div>
					)}
				</SidePanel>
			</aside>
		</>
	);
}

export default App;
