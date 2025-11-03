import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Activity, Database, GitBranch, TrendingUp } from 'lucide-react'
import { DashboardSkeleton } from '@/components/loading/DashboardSkeleton'
import { useState, useEffect } from 'react'

export default function DashboardPage() {
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // Simulate data loading
    const timer = setTimeout(() => setIsLoading(false), 1000)
    return () => clearTimeout(timer)
  }, [])

  if (isLoading) {
    return <DashboardSkeleton />
  }

  const stats = [
    {
      title: 'Total Queries',
      value: '1,234',
      description: '+20% from last month',
      icon: Activity,
    },
    {
      title: 'Active Pipelines',
      value: '12',
      description: '3 running now',
      icon: GitBranch,
    },
    {
      title: 'Data Processed',
      value: '2.4 TB',
      description: '+12% from last week',
      icon: Database,
    },
    {
      title: 'Avg Query Time',
      value: '245ms',
      description: '-8% improvement',
      icon: TrendingUp,
    },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
        <p className="text-muted-foreground">
          Overview of your data platform
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => {
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
              Chart placeholder - Recharts integration would go here
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
            <div className="space-y-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="flex items-start gap-4">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted">
                    <Activity className="h-4 w-4" />
                  </div>
                  <div className="space-y-1 flex-1">
                    <p className="text-sm font-medium">Query {i}</p>
                    <p className="text-xs text-muted-foreground">
                      Executed 2 hours ago
                    </p>
                  </div>
                  <div className="text-xs text-muted-foreground">245ms</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
