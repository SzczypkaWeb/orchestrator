import { useQuery } from '@tanstack/react-query';
import { ExternalLink } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import { Spinner } from '@/components/ui/spinner';
import type { RunGroup } from '../../../types/orchestrator';
import { fetchRunMetrics } from '../api';
import { nodeLabel, toBadgeStatus } from '../nodeLabels';

interface RunDetailsModalProps {
	run: RunGroup;
	open: boolean;
	onOpenChange: (open: boolean) => void;
	prStatus?: string;
}

function formatCost(totalCostUsd: number | null): string {
	return totalCostUsd != null ? `$${totalCostUsd.toFixed(4)}` : '—';
}

function formatTokens(
	inputTokens: number | null,
	outputTokens: number | null,
): string {
	if (inputTokens == null && outputTokens == null) return '—';
	return `${inputTokens ?? '—'} in / ${outputTokens ?? '—'} out`;
}

function formatDuration(durationMs: number): string {
	return durationMs >= 1000
		? `${(durationMs / 1000).toFixed(1)}s`
		: `${durationMs}ms`;
}

export default function RunDetailsModal({
	run,
	open,
	onOpenChange,
	prStatus,
}: RunDetailsModalProps) {
	const taskDescription = run.nodes.trigger?.detail;
	const prUrl = run.nodes.writer?.pr_url;

	const { data: metrics, isLoading: metricsLoading } = useQuery({
		queryKey: ['runMetrics', run.runId],
		queryFn: () => fetchRunMetrics(run.runId),
		enabled: open,
	});

	return (
		<Dialog
			open={open}
			onOpenChange={onOpenChange}>
			<DialogContent
				// Radix warns when a dialog has no description; none is needed here.
				aria-describedby={undefined}>
				<DialogTitle>{`${run.repo} · ${run.runId.slice(0, 8)}`}</DialogTitle>
			<div className="flex flex-col gap-4">
				{taskDescription && (
					<section>
						<h4 className="text-xs font-semibold uppercase text-muted-foreground">
							Task description
						</h4>
						<p className="mt-1 whitespace-pre-wrap text-sm text-foreground">
							{taskDescription}
						</p>
					</section>
				)}

				<section>
					<h4 className="text-xs font-semibold uppercase text-muted-foreground">
						Status
					</h4>
					<div className="mt-1 flex flex-wrap items-center gap-2">
						{Object.entries(run.nodes)
							.filter(([node]) => node !== 'trigger')
							.map(([node, event]) => (
								<div
									key={node}
									className="flex items-center gap-1.5">
									<span className="text-sm">{nodeLabel(node)}</span>
									<Badge status={toBadgeStatus(event.status)} />
								</div>
							))}
					</div>
				</section>

				{prUrl && (
					<section>
						<h4 className="text-xs font-semibold uppercase text-muted-foreground">
							Pull request
						</h4>
						<div className="mt-1 flex items-center gap-2">
							<a
								href={prUrl}
								target="_blank"
								rel="noreferrer noopener"
								className="inline-flex items-center gap-1 text-sm text-primary hover:underline">
								View PR
								<ExternalLink
									className="h-3.5 w-3.5"
									aria-hidden
								/>
							</a>
							{prStatus && (
								<span className="text-xs text-muted-foreground">
									({prStatus})
								</span>
							)}
						</div>
					</section>
				)}

				<section>
					<h4 className="text-xs font-semibold uppercase text-muted-foreground">
						Token usage & cost
					</h4>
					{metricsLoading ? (
						<div className="mt-2 flex items-center gap-2">
							<Spinner />
							<span className="text-sm text-muted-foreground">
								Loading metrics...
							</span>
						</div>
					) : metrics && metrics.length > 0 ? (
						<div className="mt-1 flex flex-col gap-2">
							{metrics.map((metric, index) => (
								<div
									key={index}
									className="flex flex-col gap-0.5 rounded border border-border p-2 text-sm">
									<div className="flex items-center justify-between gap-2">
										<span className="font-medium">
											{nodeLabel(metric.node)}
										</span>
										<span className="text-xs text-muted-foreground">
											{metric.provider}/{metric.model}
										</span>
									</div>
									<div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
										<span>
											{formatTokens(metric.inputTokens, metric.outputTokens)}{' '}
											tokens
										</span>
										<span>{formatCost(metric.totalCostUsd)}</span>
										<span>{formatDuration(metric.durationMs)}</span>
									</div>
									{!metric.success && metric.errorMessage && (
										<p className="text-xs text-destructive">
											{metric.errorMessage}
										</p>
									)}
								</div>
							))}
						</div>
					) : (
						<p className="mt-1 text-sm text-muted-foreground">
							No telemetry recorded for this run.
						</p>
					)}
				</section>
			</div>
			</DialogContent>
		</Dialog>
	);
}
