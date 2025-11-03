import { FormEvent } from 'react'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { useAnnounce } from '@/hooks/useAccessibility'

interface FormFieldProps {
  id: string
  label: string
  type?: string
  value: string
  onChange: (value: string) => void
  error?: string
  required?: boolean
  description?: string
}

export function AccessibleFormField({
  id,
  label,
  type = 'text',
  value,
  onChange,
  error,
  required,
  description,
}: FormFieldProps) {
  const errorId = `${id}-error`
  const descriptionId = `${id}-description`

  return (
    <div className="space-y-2">
      <Label htmlFor={id}>
        {label}
        {required && (
          <span className="text-destructive ml-1" aria-label="required">
            *
          </span>
        )}
      </Label>
      {description && (
        <p id={descriptionId} className="text-sm text-muted-foreground">
          {description}
        </p>
      )}
      <Input
        id={id}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-invalid={!!error}
        aria-describedby={
          error ? errorId : description ? descriptionId : undefined
        }
        aria-required={required}
      />
      {error && (
        <p id={errorId} className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}

interface AccessibleFormProps {
  onSubmit: (e: FormEvent) => void
  children: React.ReactNode
  successMessage?: string
}

export function AccessibleForm({
  onSubmit,
  children,
  successMessage,
}: AccessibleFormProps) {
  const { announce } = useAnnounce()

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    onSubmit(e)
    if (successMessage) {
      announce(successMessage, 'polite')
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      {children}
    </form>
  )
}
