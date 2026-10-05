import * as React from 'react'
import { cn } from '@/lib/utils'

// Floating surface: opaque `bg-background` so page content never bleeds through.
function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
	return (
		<div
			className={cn('rounded-lg border border-border bg-background p-4 text-foreground shadow-sm', className)}
			{...props}
		/>
	)
}

export { Card }
