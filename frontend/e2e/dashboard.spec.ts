import { test, expect } from '@playwright/test'

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto('/login')
    await page.getByLabel(/email/i).fill('test@example.com')
    await page.getByLabel(/password/i).fill('password123')
    await page.getByRole('button', { name: /sign in/i }).click()
    await expect(page).toHaveURL('/')
  })

  test('should display dashboard with stats', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /welcome back/i })).toBeVisible()

    // Check stats cards
    await expect(page.getByText(/total queries/i)).toBeVisible()
    await expect(page.getByText(/active pipelines/i)).toBeVisible()
    await expect(page.getByText(/data processed/i)).toBeVisible()
    await expect(page.getByText(/avg query time/i)).toBeVisible()
  })

  test('should display recent queries', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /recent queries/i })).toBeVisible()
    await expect(page.getByTestId('recent-queries-list')).toBeVisible()
  })

  test('should navigate to query editor from quick action', async ({ page }) => {
    await page.getByRole('button', { name: /new query/i }).click()
    await expect(page).toHaveURL('/query')
  })

  test('should display charts', async ({ page }) => {
    await expect(page.getByTestId('queries-chart')).toBeVisible()
    await expect(page.getByTestId('performance-chart')).toBeVisible()
  })

  test('should refresh data', async ({ page }) => {
    const refreshButton = page.getByRole('button', { name: /refresh/i })
    await refreshButton.click()

    // Should show loading state briefly
    await expect(page.getByTestId('dashboard-loading')).toBeVisible()

    // Then show updated data
    await expect(page.getByTestId('dashboard-loading')).not.toBeVisible()
  })
})
