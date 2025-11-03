import { NoTeamMembersEmpty } from '@/components/empty/NoTeamMembersEmpty'

export default function TeamPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Team</h2>
        <p className="text-muted-foreground">
          Manage team members and permissions
        </p>
      </div>

      <NoTeamMembersEmpty />
    </div>
  )
}
