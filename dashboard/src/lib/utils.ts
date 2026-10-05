import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

/** Standard shadcn/ui helper: merge class names, later Tailwind utilities win. */
export function cn(...inputs: ClassValue[]): string {
	return twMerge(clsx(inputs))
}
