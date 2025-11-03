import { Bell } from 'lucide-react'
import { EmptyState } from './EmptyState'

export function NoNotificationsEmpty() {
  return (
    <EmptyState
      icon={Bell}
      title="No notifications"
      description="You're all caught up! Notifications about your queries, pipelines, and team activity will appear here."
    />
  )
}
