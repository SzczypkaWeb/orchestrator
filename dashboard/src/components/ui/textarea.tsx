import * as React from 'react'
import { cn } from '@/lib/utils'

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
	/** Marks the field invalid (border + aria-invalid); render the message yourself. */
	invalid?: boolean
}

// Form control: `bg-transparent` so it blends into any surface - the visible
// border is its only boundary. Ref is forwarded as a plain prop (React 19), so
// react-hook-form's `register()` works directly.
function Textarea({ className, invalid, ...props }: TextareaProps) {
	return (
		<textarea
			aria-invalid={invalid || undefined}
			className={cn(
				'flex min-h-[80px] w-full rounded-lg border border-input bg-transparent px-3 py-2 text-sm',
				'placeholder:text-muted-foreground',
				'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
				'disabled:cursor-not-allowed disabled:opacity-50',
				invalid && 'border-destructive focus-visible:ring-destructive',
				className,
			)}
			{...props}
		/>
	)
}

export { Textarea }
