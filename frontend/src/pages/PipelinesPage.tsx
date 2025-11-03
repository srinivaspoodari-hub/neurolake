import { NoPipelinesEmpty } from '@/components/empty/NoPipelinesEmpty'

export default function PipelinesPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Pipelines</h2>
        <p className="text-muted-foreground">
          Create and manage data pipelines
        </p>
      </div>

      <NoPipelinesEmpty />
    </div>
  )
}
