import { Skeleton } from '@/components/ui/skeleton'
import { Card, CardContent, CardHeader } from '@/components/ui/card'

export function QueryEditorSkeleton() {
  return (
    <div className="space-y-4">
      {/* Editor Section */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <Skeleton className="h-6 w-32" />
          <div className="flex gap-2">
            <Skeleton className="h-9 w-20" />
            <Skeleton className="h-9 w-20" />
          </div>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[300px] w-full" />
        </CardContent>
      </Card>

      {/* Results Section */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <Skeleton className="h-6 w-24" />
            <Skeleton className="h-4 w-32" />
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {/* Table Header */}
            <div className="flex gap-4 border-b pb-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={`header-${i}`} className="h-4 flex-1" />
              ))}
            </div>
            {/* Table Rows */}
            {Array.from({ length: 10 }).map((_, rowIndex) => (
              <div key={`row-${rowIndex}`} className="flex gap-4">
                {Array.from({ length: 5 }).map((_, colIndex) => (
                  <Skeleton key={`cell-${rowIndex}-${colIndex}`} className="h-4 flex-1" />
                ))}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
