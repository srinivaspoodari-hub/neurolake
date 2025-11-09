import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { AccessibleFormField, AccessibleForm } from '@/components/forms/AccessibleForm'
import { Database } from 'lucide-react'

export default function LoginPage() {
  const navigate = useNavigate()
  const { login, error: authError, clearError, isLoading: authLoading } = useAuthStore()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState<{ username?: string; password?: string; general?: string }>({})

  const validate = () => {
    const newErrors: { username?: string; password?: string } = {}

    if (!username) {
      newErrors.username = 'Username or email is required'
    }

    if (!password) {
      newErrors.password = 'Password is required'
    } else if (password.length < 6) {
      newErrors.password = 'Password must be at least 6 characters'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    clearError()

    if (!validate()) return

    try {
      await login(username, password)
      navigate('/')
    } catch (error) {
      setErrors({ general: authError || 'Invalid credentials. Please try again.' })
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/40 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-4 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-primary">
            <Database className="h-6 w-6 text-primary-foreground" />
          </div>
          <div>
            <CardTitle className="text-2xl">Welcome to NeuroLake</CardTitle>
            <CardDescription>Sign in to your account to continue</CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          <AccessibleForm
            onSubmit={handleSubmit}
            successMessage="Successfully logged in"
          >
            <div className="space-y-4">
              {errors.general && (
                <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
                  {errors.general}
                </div>
              )}
              <AccessibleFormField
                id="username"
                label="Username or Email"
                type="text"
                value={username}
                onChange={setUsername}
                error={errors.username}
                required
              />
              <AccessibleFormField
                id="password"
                label="Password"
                type="password"
                value={password}
                onChange={setPassword}
                error={errors.password}
                required
              />
              <Button type="submit" className="w-full" disabled={authLoading}>
                {authLoading ? 'Signing in...' : 'Sign In'}
              </Button>
            </div>
          </AccessibleForm>
        </CardContent>
      </Card>
    </div>
  )
}
