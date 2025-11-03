import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Search } from 'lucide-react'
import { EmptyState } from '@/components/empty/EmptyState'

export default function HistoryPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Query History</h2>
        <p className="text-muted-foreground">
          View your past query executions
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent Queries</CardTitle>
        </CardHeader>
        <CardContent>
          <EmptyState
            icon={Search}
            title="No query history"
            description="Your executed queries will appear here once you start running queries."
          />
        </CardContent>
      </Card>
    </div>
  )
}
