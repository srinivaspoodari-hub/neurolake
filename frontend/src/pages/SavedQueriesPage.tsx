import { NoQueriesEmpty } from '@/components/empty/NoQueriesEmpty'

export default function SavedQueriesPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Saved Queries</h2>
        <p className="text-muted-foreground">
          Access your saved and bookmarked queries
        </p>
      </div>

      <NoQueriesEmpty />
    </div>
  )
}
