import * as React from 'react'
import { Select as SelectPrimitive } from 'radix-ui'
import { Check, ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'

const Select = SelectPrimitive.Root
const SelectValue = SelectPrimitive.Value

// Trigger is an inline form control -> `bg-transparent`, border-only boundary.
function SelectTrigger({ className, children, ...props }: React.ComponentProps<typeof SelectPrimitive.Trigger>) {
	return (
		<SelectPrimitive.Trigger
			className={cn(
				'flex h-10 w-full items-center justify-between rounded-lg border border-input bg-transparent px-3 py-2 text-sm',
				'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
				'disabled:cursor-not-allowed disabled:opacity-50 data-[placeholder]:text-muted-foreground',
				'aria-[invalid=true]:border-destructive',
				className,
			)}
			{...props}>
			{children}
			<SelectPrimitive.Icon asChild>
				<ChevronDown className="h-4 w-4 opacity-50" aria-hidden />
			</SelectPrimitive.Icon>
		</SelectPrimitive.Trigger>
	)
}

// The portaled panel floats over page content -> opaque `bg-background`.
function SelectContent({ className, children, ...props }: React.ComponentProps<typeof SelectPrimitive.Content>) {
	return (
		<SelectPrimitive.Portal>
			<SelectPrimitive.Content
				position="popper"
				sideOffset={4}
				className={cn(
					'relative z-50 w-[var(--radix-select-trigger-width)] min-w-[8rem] overflow-hidden rounded-lg border border-border bg-background text-foreground shadow-md',
					className,
				)}
				{...props}>
				<SelectPrimitive.Viewport className="p-1">{children}</SelectPrimitive.Viewport>
			</SelectPrimitive.Content>
		</SelectPrimitive.Portal>
	)
}

function SelectItem({ className, children, ...props }: React.ComponentProps<typeof SelectPrimitive.Item>) {
	return (
		<SelectPrimitive.Item
			className={cn(
				'relative flex w-full cursor-pointer select-none items-center rounded-sm py-1.5 pr-8 pl-2 text-sm outline-none',
				'focus:bg-muted focus:text-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50',
				className,
			)}
			{...props}>
			<SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
			<SelectPrimitive.ItemIndicator className="absolute right-2 flex items-center">
				<Check className="h-4 w-4" aria-hidden />
			</SelectPrimitive.ItemIndicator>
		</SelectPrimitive.Item>
	)
}

export { Select, SelectContent, SelectItem, SelectTrigger, SelectValue }
