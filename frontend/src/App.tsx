import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from './components/theme/ThemeProvider'
import { ErrorBoundary } from './components/error/ErrorBoundary'
import { SkipLink } from './components/accessibility/SkipLink'
import { ResponsiveLayout } from './components/layout/ResponsiveLayout'
import { useAuthStore } from './store/authStore'
import { Suspense, lazy } from 'react'
import { FullPageSpinner } from './components/loading/LoadingSpinner'

// Lazy load pages for better performance
const LoginPage = lazy(() => import('./pages/LoginPage'))
const DashboardPage = lazy(() => import('./pages/DashboardPage'))
const QueryPage = lazy(() => import('./pages/QueryPage'))
const TablesPage = lazy(() => import('./pages/TablesPage'))
const PipelinesPage = lazy(() => import('./pages/PipelinesPage'))
const HistoryPage = lazy(() => import('./pages/HistoryPage'))
const SavedQueriesPage = lazy(() => import('./pages/SavedQueriesPage'))
const TeamPage = lazy(() => import('./pages/TeamPage'))
const SettingsPage = lazy(() => import('./pages/SettingsPage'))

// Create QueryClient instance
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 1,
    },
  },
})

// Protected Route wrapper
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider defaultTheme="system">
          <BrowserRouter>
            <SkipLink />
            <Suspense fallback={<FullPageSpinner />}>
              <Routes>
                {/* Public routes */}
                <Route path="/login" element={<LoginPage />} />

                {/* Protected routes */}
                <Route
                  path="/"
                  element={
                    <ProtectedRoute>
                      <ResponsiveLayout>
                        <main id="main-content" tabIndex={-1}>
                          <DashboardPage />
                        </main>
                      </ResponsiveLayout>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/query"
                  element={
                    <ProtectedRoute>
                      <ResponsiveLayout>
                        <main id="main-content" tabIndex={-1}>
                          <QueryPage />
                        </main>
                      </ResponsiveLayout>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/tables"
                  element={
                    <ProtectedRoute>
                      <ResponsiveLayout>
                        <main id="main-content" tabIndex={-1}>
                          <TablesPage />
                        </main>
                      </ResponsiveLayout>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/pipelines"
                  element={
                    <ProtectedRoute>
                      <ResponsiveLayout>
                        <main id="main-content" tabIndex={-1}>
                          <PipelinesPage />
                        </main>
                      </ResponsiveLayout>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/history"
                  element={
                    <ProtectedRoute>
                      <ResponsiveLayout>
                        <main id="main-content" tabIndex={-1}>
                          <HistoryPage />
                        </main>
                      </ResponsiveLayout>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/saved"
                  element={
                    <ProtectedRoute>
                      <ResponsiveLayout>
                        <main id="main-content" tabIndex={-1}>
                          <SavedQueriesPage />
                        </main>
                      </ResponsiveLayout>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/team"
                  element={
                    <ProtectedRoute>
                      <ResponsiveLayout>
                        <main id="main-content" tabIndex={-1}>
                          <TeamPage />
                        </main>
                      </ResponsiveLayout>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/settings"
                  element={
                    <ProtectedRoute>
                      <ResponsiveLayout>
                        <main id="main-content" tabIndex={-1}>
                          <SettingsPage />
                        </main>
                      </ResponsiveLayout>
                    </ProtectedRoute>
                  }
                />

                {/* Catch all - redirect to home */}
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Suspense>
          </BrowserRouter>
        </ThemeProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  )
}

export default App
