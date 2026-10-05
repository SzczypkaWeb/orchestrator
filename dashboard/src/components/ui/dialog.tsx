import * as React from 'react'
import { Dialog as DialogPrimitive } from 'radix-ui'
import { X } from 'lucide-react'
import { cn } from '@/lib/utils'

const Dialog = DialogPrimitive.Root

function DialogContent({
	className,
	children,
	...props
}: React.ComponentProps<typeof DialogPrimitive.Content>) {
	return (
		<DialogPrimitive.Portal>
			<DialogPrimitive.Overlay className="fixed inset-0 bg-black/50 data-[state=closed]:animate-out data-[state=open]:animate-in data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
			{/* Floating surface: opaque bg-background (the dialog sits over arbitrary page content). */}
			<DialogPrimitive.Content
				className={cn(
					'fixed top-1/2 left-1/2 max-h-[85vh] w-full max-w-3xl -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-lg border border-border bg-background p-6 text-foreground shadow-lg',
					className,
				)}
				{...props}>
				{children}
				<DialogPrimitive.Close
					aria-label="Close"
					className="absolute top-3 right-3 flex h-7 w-7 items-center justify-center rounded-full hover:bg-black/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring dark:hover:bg-white/10">
					<X className="h-4 w-4" aria-hidden />
				</DialogPrimitive.Close>
			</DialogPrimitive.Content>
		</DialogPrimitive.Portal>
	)
}

function DialogTitle({ className, ...props }: React.ComponentProps<typeof DialogPrimitive.Title>) {
	return <DialogPrimitive.Title className={cn('pb-4 text-lg font-semibold leading-none tracking-tight', className)} {...props} />
}

function DialogDescription(props: React.ComponentProps<typeof DialogPrimitive.Description>) {
	return <DialogPrimitive.Description {...props} />
}

export { Dialog, DialogContent, DialogDescription, DialogTitle }
