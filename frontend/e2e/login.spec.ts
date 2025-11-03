import { test, expect } from '@playwright/test'

test.describe('Authentication', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
  })

  test('should display login form', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /sign in/i })).toBeVisible()
    await expect(page.getByLabel(/email/i)).toBeVisible()
    await expect(page.getByLabel(/password/i)).toBeVisible()
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible()
  })

  test('should show validation errors for empty fields', async ({ page }) => {
    await page.getByRole('button', { name: /sign in/i }).click()

    await expect(page.getByText(/email is required/i)).toBeVisible()
    await expect(page.getByText(/password is required/i)).toBeVisible()
  })

  test('should show error for invalid email format', async ({ page }) => {
    await page.getByLabel(/email/i).fill('invalid-email')
    await page.getByLabel(/password/i).fill('password123')
    await page.getByRole('button', { name: /sign in/i }).click()

    await expect(page.getByText(/invalid email/i)).toBeVisible()
  })

  test('should successfully log in with valid credentials', async ({ page }) => {
    await page.getByLabel(/email/i).fill('test@example.com')
    await page.getByLabel(/password/i).fill('password123')
    await page.getByRole('button', { name: /sign in/i }).click()

    // Should redirect to dashboard
    await expect(page).toHaveURL('/')
    await expect(page.getByRole('heading', { name: /welcome back/i })).toBeVisible()
  })

  test('should persist authentication after page reload', async ({ page }) => {
    // Login
    await page.getByLabel(/email/i).fill('test@example.com')
    await page.getByLabel(/password/i).fill('password123')
    await page.getByRole('button', { name: /sign in/i }).click()

    await expect(page).toHaveURL('/')

    // Reload page
    await page.reload()

    // Should still be on dashboard
    await expect(page).toHaveURL('/')
    await expect(page.getByRole('heading', { name: /welcome back/i })).toBeVisible()
  })

  test('should logout successfully', async ({ page }) => {
    // Login first
    await page.getByLabel(/email/i).fill('test@example.com')
    await page.getByLabel(/password/i).fill('password123')
    await page.getByRole('button', { name: /sign in/i }).click()

    await expect(page).toHaveURL('/')

    // Click user menu
    await page.getByRole('button', { name: /user menu/i }).click()

    // Click logout
    await page.getByRole('menuitem', { name: /logout/i }).click()

    // Should redirect to login
    await expect(page).toHaveURL('/login')
  })

  test('should be accessible', async ({ page }) => {
    // Check for proper ARIA labels
    await expect(page.getByLabel(/email/i)).toHaveAttribute('aria-required', 'true')
    await expect(page.getByLabel(/password/i)).toHaveAttribute('aria-required', 'true')

    // Check keyboard navigation
    await page.keyboard.press('Tab')
    await expect(page.getByLabel(/email/i)).toBeFocused()

    await page.keyboard.press('Tab')
    await expect(page.getByLabel(/password/i)).toBeFocused()

    await page.keyboard.press('Tab')
    await expect(page.getByRole('button', { name: /sign in/i })).toBeFocused()
  })
})
