import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Play } from 'lucide-react'

export default function QueryPage() {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Query Editor</h2>
        <p className="text-muted-foreground">
          Write and execute SQL queries
        </p>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>SQL Editor</CardTitle>
          <Button>
            <Play className="mr-2 h-4 w-4" />
            Execute
          </Button>
        </CardHeader>
        <CardContent>
          <div className="h-[300px] rounded-md border bg-muted/40 flex items-center justify-center text-muted-foreground">
            SQL Editor placeholder - CodeMirror integration would go here
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Results</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[200px] rounded-md border bg-muted/40 flex items-center justify-center text-muted-foreground">
            Results table placeholder
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
