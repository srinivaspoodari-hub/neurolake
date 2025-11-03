import { Search } from 'lucide-react'
import { EmptyState } from './EmptyState'
import { useNavigate } from 'react-router-dom'

export function NoQueriesEmpty() {
  const navigate = useNavigate()

  return (
    <EmptyState
      icon={Search}
      title="No saved queries"
      description="Save your frequently used queries for quick access later. Start by running a query and clicking the save button."
      action={{
        label: 'Go to Query Editor',
        onClick: () => navigate('/query'),
      }}
    />
  )
}
