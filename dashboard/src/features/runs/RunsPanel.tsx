import { useVirtualizer } from '@tanstack/react-virtual';
import { useRef } from 'react';
import { useRunList } from './useRunList';
import type { OrchestratorEvent } from '../../types/orchestrator';
import { Spinner } from '@/components/ui/spinner';
import RunCard from './components/RunCard';

export function RunsPanel({ events }: { events: OrchestratorEvent[] }) {
	const parentRef = useRef<HTMLDivElement>(null);
	const { historyLoading, activeRuns, historyRuns, completeRunMutation } =
		useRunList(events);

	const virtualizer = useVirtualizer({
		count: historyRuns.length,
		getScrollElement: () => parentRef.current,
		estimateSize: () => 80, // initial guess only - measureElement (below) corrects it per-card once rendered
		overscan: 5,
	});

	return (
		<aside className="fixed top-4 right-4 bottom-4">
			{/* Page chrome (not a floating surface): transparent, border only. */}
			<div className="flex h-full w-72 flex-col border-r border-border bg-transparent text-foreground">
				{historyLoading ? (
					<div className="flex items-center justify-center gap-2 p-6">
						<Spinner />
						<span className="text-sm text-muted-foreground">
							Loading history...
						</span>
					</div>
				) : (
					<div className="flex min-h-0 flex-1 flex-col">
						{activeRuns.length > 0 && (
							<div className="flex max-h-[50%] flex-col gap-2 overflow-y-auto border-b border-border p-3">
								<p className="text-xs font-semibold uppercase text-muted-foreground">
									Active
								</p>
								{activeRuns.map(
									({ run, prStatus, prStatusLoading, isComplete }) => (
										<RunCard
											key={run.runId}
											run={run}
											prStatus={prStatus}
											prStatusLoading={prStatusLoading}
											isComplete={isComplete}
											onMarkComplete={() =>
												completeRunMutation.mutate({
													runId: run.runId,
													repo: run.repo,
												})
											}
											markCompletePending={
												completeRunMutation.isPending &&
												completeRunMutation.variables?.runId === run.runId
											}
										/>
									),
								)}
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
			</div>
		</aside>
	);
}
