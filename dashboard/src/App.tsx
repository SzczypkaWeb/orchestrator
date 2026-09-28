import './App.css';

import { useOrchestratorEvents } from './features/connection-status/useOrchestratorEvents';
import ConnectionStatusBanner from './features/connection-status/ConnectionStatusBanner';
import TriggerForm from './features/trigger-form/TriggerForm';

import { RunsPanel } from './features/runs/RunsPanel';

function App() {
	const { status, events } = useOrchestratorEvents();

	return (
		<>
			<main id="center">
				<h1>Orchestrator</h1>

				<TriggerForm />

				<ConnectionStatusBanner status={status} />
			</main>

			<RunsPanel events={events} />
		</>
	);
}

export default App;
