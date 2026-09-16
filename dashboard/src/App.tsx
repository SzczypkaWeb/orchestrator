import './App.css';
import { Controller, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation } from '@tanstack/react-query';
import { z } from 'zod';
import { Button, Select, TextArea } from '@szczypkaweb/shared-ui';
import useRepoOptions from './hooks/useRepoOptions';
import { triggerRun } from './api/runs';
import useOrchestratorEvents from './hooks/useOrchestratorEvents';

const schema = z.object({
	task: z
		.string()
		.min(10, 'Describe the task in more detail (min. 10 characters).'),
	repo: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

function App() {
	const { options: repoOptions, isError: reposFailedToLoad } = useRepoOptions();
	const { events, status } = useOrchestratorEvents();

	const {
		register,
		handleSubmit,
		control,
		reset,
		formState: { errors },
	} = useForm<FormValues>({
		resolver: zodResolver(schema),
		defaultValues: { task: '', repo: '' },
	});

	const mutation = useMutation({
		mutationFn: (values: FormValues) =>
			triggerRun({ task: values.task, repo: values.repo || undefined }),
		onSuccess: () => reset(),
	});

	return (
		<main id="center">
			<h1>Orchestrator</h1>

			<form
				onSubmit={handleSubmit((values) => mutation.mutate(values))}
				className="flex w-full max-w-md flex-col gap-4 text-left">
				<TextArea
					placeholder="Describe what should be built..."
					error={errors.task?.message}
					rows={5}
					{...register('task')}
				/>

				<Controller
					name="repo"
					control={control}
					render={({ field }) => (
						<Select
							options={repoOptions}
							placeholder="Auto"
							error={
								reposFailedToLoad ? 'Could not load the repo list.' : undefined
							}
							{...field}
						/>
					)}
				/>

				<Button
					type="submit"
					disabled={mutation.isPending}>
					{mutation.isPending ? 'Starting...' : 'Trigger task'}
				</Button>

				{mutation.isError && (
					<p
						role="alert"
						className="text-sm text-red-600">
						{mutation.error.message}
					</p>
				)}
				{mutation.isSuccess && (
					<p
						role="status"
						className="text-sm text-green-700">
						Task started.
					</p>
				)}
			</form>

			{status !== 'open' && (
				<p
					role="status"
					className="text-sm text-amber-600">
					{status === 'connecting'
						? 'Łączenie z orchestratorem...'
						: 'Rozłączono z orchestratorem.'}
				</p>
			)}
		</main>
	);
}

export default App;
