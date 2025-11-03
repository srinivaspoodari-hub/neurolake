import { Database } from 'lucide-react'
import { EmptyState } from './EmptyState'

interface NoTablesEmptyProps {
  onCreateTable?: () => void
}

export function NoTablesEmpty({ onCreateTable }: NoTablesEmptyProps) {
  return (
    <EmptyState
      icon={Database}
      title="No tables found"
      description="Get started by creating your first table or importing data from an external source."
      action={
        onCreateTable
          ? {
              label: 'Create Table',
              onClick: onCreateTable,
            }
          : undefined
      }
    />
  )
}
