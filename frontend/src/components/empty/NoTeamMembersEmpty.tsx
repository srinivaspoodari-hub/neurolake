import { Users } from 'lucide-react'
import { EmptyState } from './EmptyState'

interface NoTeamMembersEmptyProps {
  onInvite?: () => void
}

export function NoTeamMembersEmpty({ onInvite }: NoTeamMembersEmptyProps) {
  return (
    <EmptyState
      icon={Users}
      title="No team members yet"
      description="Collaborate with your team by inviting members. They'll be able to access shared resources based on their role."
      action={
        onInvite
          ? {
              label: 'Invite Team Member',
              onClick: onInvite,
            }
          : undefined
      }
    />
  )
}
