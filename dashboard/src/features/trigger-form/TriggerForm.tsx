import { Controller, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation } from '@tanstack/react-query';
import z from 'zod';
import { Button, Select, TextArea } from '@szczypkaweb/shared-ui';
import { triggerRun } from '../../api/runs';
import useRepoOptions from './useRepoOptions';

const schema = z.object({
	task: z
		.string()
		.min(10, 'Describe the task in more detail (min. 10 characters).'),
	repo: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

/**
 * The task-submission form - repo picker + task description + submit.
 * Fully self-contained: owns its own form state, repo options, and the
 * trigger mutation, so App.tsx just renders <TriggerForm /> with no props.
 */
export default function TriggerForm() {
	const { options: repoOptions, isError: reposFailedToLoad } = useRepoOptions();

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
		<form
			onSubmit={handleSubmit((values) => mutation.mutate(values))}
			className="flex w-full max-w-md flex-col gap-4 text-left">
			<TextArea
				placeholder="Describe what should be built..."
				error={errors.task?.message}
				rows={5}
				{...register('task')}
			/>

			<div className="flex gap-4">
				<Controller
					name="repo"
					control={control}
					render={({ field }) => (
						<Select
							options={repoOptions}
							placeholder="Auto"
							error={
								reposFailedToLoad
									? 'Could not load the repo list.'
									: undefined
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
			</div>

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
	);
}
