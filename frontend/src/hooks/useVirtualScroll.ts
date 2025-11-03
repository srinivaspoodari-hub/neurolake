import { useVirtualizer } from '@tanstack/react-virtual'
import { useRef } from 'react'

interface UseVirtualScrollProps<T> {
  items: T[]
  estimateSize?: number
  overscan?: number
}

export function useVirtualScroll<T>({
  items,
  estimateSize = 50,
  overscan = 5,
}: UseVirtualScrollProps<T>) {
  const parentRef = useRef<HTMLDivElement>(null)

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => estimateSize,
    overscan,
  })

  return {
    parentRef,
    virtualizer,
    virtualItems: virtualizer.getVirtualItems(),
    totalSize: virtualizer.getTotalSize(),
  }
}
