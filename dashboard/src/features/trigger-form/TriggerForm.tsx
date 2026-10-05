import { Controller, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation } from '@tanstack/react-query';
import z from 'zod';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { triggerRun } from '../runs/api';
import useRepoOptions, { AUTO_REPO } from './useRepoOptions';

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
		defaultValues: { task: '', repo: AUTO_REPO },
	});

	const mutation = useMutation({
		mutationFn: (values: FormValues) =>
			triggerRun({ task: values.task, repo: values.repo && values.repo !== AUTO_REPO ? values.repo : undefined }),
		onSuccess: () => reset(),
	});

	return (
		<form
			onSubmit={handleSubmit((values) => mutation.mutate(values))}
			className="flex w-full max-w-md flex-col gap-4 text-left">
			<div>
				<Textarea
					placeholder="Describe what should be built..."
					invalid={!!errors.task}
					aria-describedby={errors.task ? 'task-error' : undefined}
					rows={5}
					{...register('task')}
				/>
				{errors.task && (
					<p
						id="task-error"
						role="alert"
						className="mt-1 text-sm text-destructive">
						{errors.task.message}
					</p>
				)}
			</div>

			<div className="flex items-start gap-4">
				<div className="w-full">
					<Controller
						name="repo"
						control={control}
						render={({ field }) => (
							<Select
								name={field.name}
								value={field.value}
								onValueChange={field.onChange}>
								<SelectTrigger
									ref={field.ref}
									onBlur={field.onBlur}
									aria-invalid={reposFailedToLoad || undefined}>
									<SelectValue placeholder="Auto" />
								</SelectTrigger>
								<SelectContent>
									{repoOptions.map((option) => (
										<SelectItem
											key={option.value}
											value={option.value}>
											{option.label}
										</SelectItem>
									))}
								</SelectContent>
							</Select>
						)}
					/>
					{reposFailedToLoad && (
						<p
							role="alert"
							className="mt-1 text-sm text-destructive">
							Could not load the repo list.
						</p>
					)}
				</div>

				<Button
					type="submit"
					disabled={mutation.isPending}>
					{mutation.isPending ? 'Starting...' : 'Trigger task'}
				</Button>
			</div>

			{mutation.isError && (
				<p
					role="alert"
					className="text-sm text-destructive">
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
