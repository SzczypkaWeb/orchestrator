import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

// One hue per run status, so (unlike most components) these don't map onto a
// single semantic token - each variant carries its own explicit `dark:` pair.
const badgeVariants = cva('inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium', {
	variants: {
		variant: {
			running: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
			done: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
			blocked: 'bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-200',
			failed: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
			approved: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200',
			changes_requested: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200',
		},
	},
	defaultVariants: { variant: 'running' },
})

export type BadgeStatus = NonNullable<VariantProps<typeof badgeVariants>['variant']>

const LABELS: Record<BadgeStatus, string> = {
	running: 'Running',
	done: 'Done',
	blocked: 'Blocked',
	failed: 'Failed',
	approved: 'Approved',
	changes_requested: 'Changes requested',
}

export interface BadgeProps extends Omit<React.HTMLAttributes<HTMLSpanElement>, 'children'> {
	status: BadgeStatus
}

/** Pill showing a run/node status (label + colour derive from `status`). */
function Badge({ status, className, ...props }: BadgeProps) {
	return (
		<span className={cn(badgeVariants({ variant: status }), className)} {...props}>
			{LABELS[status]}
		</span>
	)
}

export { Badge, badgeVariants }
