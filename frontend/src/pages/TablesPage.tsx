import { NoTablesEmpty } from '@/components/empty/NoTablesEmpty'

export default function TablesPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Tables</h2>
        <p className="text-muted-foreground">
          Browse and manage your data tables
        </p>
      </div>

      <NoTablesEmpty />
    </div>
  )
}
