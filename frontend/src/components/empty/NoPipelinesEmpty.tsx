import { GitBranch } from 'lucide-react'
import { EmptyState } from './EmptyState'

interface NoPipelinesEmptyProps {
  onCreatePipeline?: () => void
}

export function NoPipelinesEmpty({ onCreatePipeline }: NoPipelinesEmptyProps) {
  return (
    <EmptyState
      icon={GitBranch}
      title="No pipelines configured"
      description="Create data pipelines to automate your data processing workflows. Build, schedule, and monitor pipelines visually."
      action={
        onCreatePipeline
          ? {
              label: 'Create Pipeline',
              onClick: onCreatePipeline,
            }
          : undefined
      }
    />
  )
}
