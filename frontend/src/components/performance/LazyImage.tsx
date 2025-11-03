import { useState } from 'react'
import { useIntersectionObserver } from '@/hooks/useIntersectionObserver'
import { cn } from '@/lib/utils'
import { Skeleton } from '@/components/ui/skeleton'

interface LazyImageProps {
  src: string
  alt: string
  className?: string
  width?: number
  height?: number
}

export function LazyImage({ src, alt, className, width, height }: LazyImageProps) {
  const [isLoaded, setIsLoaded] = useState(false)
  const [isInView, setIsInView] = useState(false)
  const [setRef, entry] = useIntersectionObserver({
    threshold: 0.1,
    rootMargin: '50px',
  })

  if (entry?.isIntersecting && !isInView) {
    setIsInView(true)
  }

  return (
    <div
      ref={setRef as (node: HTMLDivElement) => void}
      className={cn('relative overflow-hidden', className)}
      style={{ width, height }}
    >
      {!isLoaded && <Skeleton className="absolute inset-0" />}
      {isInView && (
        <img
          src={src}
          alt={alt}
          loading="lazy"
          className={cn(
            'transition-opacity duration-300',
            isLoaded ? 'opacity-100' : 'opacity-0'
          )}
          onLoad={() => setIsLoaded(true)}
          width={width}
          height={height}
        />
      )}
    </div>
  )
}
