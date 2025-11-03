import { AlertCircle, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

interface QueryErrorProps {
  error: Error | null
  onRetry?: () => void
  title?: string
}

export function QueryError({ error, onRetry, title = 'Query Failed' }: QueryErrorProps) {
  if (!error) return null

  return (
    <Alert variant="destructive">
      <AlertCircle className="h-4 w-4" />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription className="mt-2 space-y-2">
        <p className="text-sm">{error.message}</p>
        {onRetry && (
          <Button
            variant="outline"
            size="sm"
            onClick={onRetry}
            className="mt-2"
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            Retry
          </Button>
        )}
      </AlertDescription>
    </Alert>
  )
}
