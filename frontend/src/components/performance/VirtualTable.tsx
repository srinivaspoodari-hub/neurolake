import { useVirtualScroll } from '@/hooks/useVirtualScroll'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

interface Column<T> {
  key: string
  header: string
  render: (item: T) => React.ReactNode
  width?: string
}

interface VirtualTableProps<T> {
  data: T[]
  columns: Column<T>[]
  rowHeight?: number
  maxHeight?: string
}

export function VirtualTable<T>({
  data,
  columns,
  rowHeight = 50,
  maxHeight = '600px',
}: VirtualTableProps<T>) {
  const { parentRef, virtualItems, totalSize } = useVirtualScroll({
    items: data,
    estimateSize: rowHeight,
  })

  return (
    <div
      ref={parentRef}
      className="overflow-auto border rounded-md"
      style={{ maxHeight }}
    >
      <Table>
        <TableHeader className="sticky top-0 bg-background z-10">
          <TableRow>
            {columns.map((column) => (
              <TableHead
                key={column.key}
                style={{ width: column.width }}
              >
                {column.header}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          <tr style={{ height: totalSize }}>
            <td style={{ position: 'relative' }}>
              {virtualItems.map((virtualRow) => {
                const item = data[virtualRow.index]
                return (
                  <TableRow
                    key={virtualRow.index}
                    style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      width: '100%',
                      transform: `translateY(${virtualRow.start}px)`,
                    }}
                  >
                    {columns.map((column) => (
                      <TableCell key={column.key} style={{ width: column.width }}>
                        {column.render(item)}
                      </TableCell>
                    ))}
                  </TableRow>
                )
              })}
            </td>
          </tr>
        </TableBody>
      </Table>
    </div>
  )
}
