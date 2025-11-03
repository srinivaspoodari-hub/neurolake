import { cn } from '@/lib/utils'

interface VisuallyHiddenProps {
  children: React.ReactNode
  className?: string
}

// Component for screen reader only text
export function VisuallyHidden({ children, className }: VisuallyHiddenProps) {
  return (
    <span className={cn('sr-only', className)}>
      {children}
    </span>
  )
}
