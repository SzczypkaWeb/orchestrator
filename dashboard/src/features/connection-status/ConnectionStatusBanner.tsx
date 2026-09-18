import type { ConnectionStatus } from '../../types/orchestrator';

interface ConnectionStatusBannerProps {
	status: ConnectionStatus;
}

export default function ConnectionStatusBanner({
	status,
}: ConnectionStatusBannerProps) {
	if (status === 'open') return null;

	return (
		<p
			role="status"
			className="text-sm text-amber-600">
			{status === 'connecting'
				? 'Connecting to the orchestrator...'
				: 'Disconnected from the orchestrator.'}
		</p>
	);
}
