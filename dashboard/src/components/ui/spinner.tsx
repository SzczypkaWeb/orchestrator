import * as React from 'react'
import { cn } from '@/lib/utils'

const SIZES = { sm: 'h-4 w-4', md: 'h-6 w-6' } as const

export interface SpinnerProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'children'> {
	size?: keyof typeof SIZES
	/** Screen-reader label. */
	label?: string
}

function Spinner({ size = 'sm', label = 'Loading...', className, ...props }: SpinnerProps) {
	return (
		<div role="status" aria-live="polite" className={className} {...props}>
			<div className={cn('animate-spin rounded-full border-2 border-muted border-t-primary', SIZES[size])} />
			<span className="sr-only">{label}</span>
		</div>
	)
}

export { Spinner }
