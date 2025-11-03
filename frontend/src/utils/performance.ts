// Memoization helper for expensive computations
export function memoize<T extends (...args: any[]) => any>(fn: T): T {
  const cache = new Map()

  return ((...args: Parameters<T>) => {
    const key = JSON.stringify(args)
    if (cache.has(key)) {
      return cache.get(key)
    }
    const result = fn(...args)
    cache.set(key, result)
    return result
  }) as T
}

// Throttle function for limiting execution rate
export function throttle<T extends (...args: any[]) => any>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let lastCall = 0
  return (...args: Parameters<T>) => {
    const now = Date.now()
    if (now - lastCall < delay) {
      return
    }
    lastCall = now
    return fn(...args)
  }
}

// Debounce function for delaying execution
export function debounce<T extends (...args: any[]) => any>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: NodeJS.Timeout
  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId)
    timeoutId = setTimeout(() => fn(...args), delay)
  }
}

// Batch multiple updates into a single render
export function batchUpdates<T>(
  updates: (() => void)[],
  callback?: () => void
): void {
  requestAnimationFrame(() => {
    updates.forEach(update => update())
    callback?.()
  })
}

// Lazy load modules
export async function lazyLoadModule<T>(
  importFn: () => Promise<T>
): Promise<T> {
  try {
    return await importFn()
  } catch (error) {
    console.error('Failed to load module:', error)
    throw error
  }
}
