import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Activity, Database, GitBranch, TrendingUp, Clock } from 'lucide-react'
import { DashboardSkeleton } from '@/components/loading/DashboardSkeleton'
import { useDashboardStats, useRecentQueries } from '@/hooks/useDashboard'

export default function DashboardPage() {
  const { data: stats, isLoading: statsLoading } = useDashboardStats()
  const { data: recentQueries, isLoading: queriesLoading } = useRecentQueries(5)

  if (statsLoading) {
    return <DashboardSkeleton />
  }

  const statsCards = [
    {
      title: 'Total Queries',
      value: stats?.totalQueries.toLocaleString() || '0',
      description: 'Executed queries',
      icon: Activity,
    },
    {
      title: 'Active Pipelines',
      value: stats?.activePipelines.toString() || '0',
      description: 'Running pipelines',
      icon: GitBranch,
    },
    {
      title: 'Data Processed',
      value: stats?.dataProcessed || '0 TB',
      description: 'Total data volume',
      icon: Database,
    },
    {
      title: 'Avg Query Time',
      value: stats?.avgQueryTime || '0ms',
      description: 'Average execution time',
      icon: TrendingUp,
    },
  ]

  const formatTimeAgo = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)

    if (diffMins < 1) return 'just now'
    if (diffMins < 60) return `${diffMins}m ago`
    const diffHours = Math.floor(diffMins / 60)
    if (diffHours < 24) return `${diffHours}h ago`
    const diffDays = Math.floor(diffHours / 24)
    return `${diffDays}d ago`
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
        <p className="text-muted-foreground">
          Overview of your data platform
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {statsCards.map((stat) => {
          const Icon = stat.icon
          return (
            <Card key={stat.title}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {stat.title}
                </CardTitle>
                <Icon className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stat.value}</div>
                <p className="text-xs text-muted-foreground">
                  {stat.description}
                </p>
              </CardContent>
            </Card>
          )
        })}
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        <Card className="col-span-4">
          <CardHeader>
            <CardTitle>Query Activity</CardTitle>
            <CardDescription>
              Your query execution over the last 7 days
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px] flex items-center justify-center text-muted-foreground">
              Chart visualization coming soon - Connect Recharts to query metrics
            </div>
          </CardContent>
        </Card>

        <Card className="col-span-3">
          <CardHeader>
            <CardTitle>Recent Queries</CardTitle>
            <CardDescription>
              Your most recent query executions
            </CardDescription>
          </CardHeader>
          <CardContent>
            {queriesLoading ? (
              <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-16 animate-pulse rounded-md bg-muted" />
                ))}
              </div>
            ) : recentQueries && recentQueries.length > 0 ? (
              <div className="space-y-4">
                {recentQueries.map((query) => (
                  <div key={query.query_id} className="flex items-start justify-between border-b pb-3 last:border-0">
                    <div className="flex-1 space-y-1">
                      <p className="text-sm font-mono text-muted-foreground line-clamp-2">
                        {query.sql}
                      </p>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <Clock className="h-3 w-3" />
                        <span>{query.execution_time_ms}ms</span>
                        <span>•</span>
                        <span>{query.row_count} rows</span>
                        <span>•</span>
                        <span>{formatTimeAgo(query.timestamp)}</span>
                      </div>
                    </div>
                    <div className={`ml-4 rounded-full px-2 py-1 text-xs ${
                      query.status === 'success'
                        ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                        : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                    }`}>
                      {query.status}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
                No recent queries. Execute your first query to see it here!
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
