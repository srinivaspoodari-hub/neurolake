import { test, expect } from '@playwright/test'

test.describe('Query Editor', () => {
  test.beforeEach(async ({ page }) => {
    // Login first
    await page.goto('/login')
    await page.getByLabel(/email/i).fill('test@example.com')
    await page.getByLabel(/password/i).fill('password123')
    await page.getByRole('button', { name: /sign in/i }).click()
    await expect(page).toHaveURL('/')

    // Navigate to query editor
    await page.getByRole('link', { name: /query/i }).click()
    await expect(page).toHaveURL('/query')
  })

  test('should display query editor interface', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /query editor/i })).toBeVisible()
    await expect(page.getByTestId('sql-editor')).toBeVisible()
    await expect(page.getByRole('button', { name: /execute/i })).toBeVisible()
  })

  test('should write and execute SQL query', async ({ page }) => {
    const query = 'SELECT * FROM users LIMIT 10'

    // Type query
    await page.getByTestId('sql-editor').click()
    await page.keyboard.type(query)

    // Execute query
    await page.getByRole('button', { name: /execute/i }).click()

    // Wait for results
    await expect(page.getByTestId('query-results')).toBeVisible()
    await expect(page.getByRole('table')).toBeVisible()
  })

  test('should show syntax highlighting', async ({ page }) => {
    const query = 'SELECT name, email FROM users WHERE active = true'

    await page.getByTestId('sql-editor').click()
    await page.keyboard.type(query)

    // Check for syntax highlighting classes (CodeMirror specific)
    const editor = page.getByTestId('sql-editor')
    await expect(editor.locator('.cm-keyword')).toHaveCount(3) // SELECT, FROM, WHERE
  })

  test('should provide autocomplete suggestions', async ({ page }) => {
    await page.getByTestId('sql-editor').click()
    await page.keyboard.type('SEL')

    // Wait for autocomplete
    await expect(page.getByRole('listbox')).toBeVisible()
    await expect(page.getByRole('option', { name: /SELECT/i })).toBeVisible()

    // Select suggestion
    await page.keyboard.press('Enter')

    const editorText = await page.getByTestId('sql-editor').textContent()
    expect(editorText).toContain('SELECT')
  })

  test('should switch between SQL and natural language input', async ({ page }) => {
    // Click natural language tab
    await page.getByRole('tab', { name: /natural language/i }).click()

    await expect(page.getByPlaceholder(/ask a question/i)).toBeVisible()

    // Type natural language query
    await page.getByPlaceholder(/ask a question/i).fill('Show me all active users')
    await page.getByRole('button', { name: /convert to sql/i }).click()

    // Should switch to SQL tab with generated query
    await expect(page.getByRole('tab', { name: /sql/i })).toHaveAttribute('aria-selected', 'true')
    await expect(page.getByTestId('sql-editor')).toContainText('SELECT')
  })

  test('should display query results in table format', async ({ page }) => {
    const query = 'SELECT * FROM users LIMIT 5'

    await page.getByTestId('sql-editor').click()
    await page.keyboard.type(query)
    await page.getByRole('button', { name: /execute/i }).click()

    // Check results table
    await expect(page.getByRole('table')).toBeVisible()
    await expect(page.getByRole('columnheader')).toHaveCount(5) // Assuming 5 columns
    await expect(page.getByRole('row')).toHaveCount(6) // 5 data rows + 1 header
  })

  test('should export query results', async ({ page }) => {
    const query = 'SELECT * FROM users LIMIT 5'

    await page.getByTestId('sql-editor').click()
    await page.keyboard.type(query)
    await page.getByRole('button', { name: /execute/i }).click()

    await expect(page.getByRole('table')).toBeVisible()

    // Click export button
    const downloadPromise = page.waitForEvent('download')
    await page.getByRole('button', { name: /export/i }).click()
    await page.getByRole('menuitem', { name: /csv/i }).click()

    const download = await downloadPromise
    expect(download.suggestedFilename()).toMatch(/\.csv$/)
  })

  test('should visualize results with charts', async ({ page }) => {
    const query = 'SELECT status, COUNT(*) as count FROM users GROUP BY status'

    await page.getByTestId('sql-editor').click()
    await page.keyboard.type(query)
    await page.getByRole('button', { name: /execute/i }).click()

    await expect(page.getByRole('table')).toBeVisible()

    // Switch to chart view
    await page.getByRole('tab', { name: /chart/i }).click()

    // Check chart is rendered
    await expect(page.getByTestId('chart-container')).toBeVisible()

    // Switch chart types
    await page.getByRole('button', { name: /bar chart/i }).click()
    await page.getByRole('menuitem', { name: /pie chart/i }).click()

    await expect(page.getByTestId('pie-chart')).toBeVisible()
  })

  test('should save query', async ({ page }) => {
    const query = 'SELECT * FROM users WHERE role = "admin"'

    await page.getByTestId('sql-editor').click()
    await page.keyboard.type(query)

    // Click save button
    await page.getByRole('button', { name: /save/i }).click()

    // Fill save dialog
    await page.getByLabel(/query name/i).fill('Admin Users Query')
    await page.getByLabel(/description/i).fill('Get all admin users')
    await page.getByRole('button', { name: /save query/i }).click()

    // Should show success message
    await expect(page.getByText(/query saved/i)).toBeVisible()
  })

  test('should show query history', async ({ page }) => {
    // Execute a query
    await page.getByTestId('sql-editor').click()
    await page.keyboard.type('SELECT * FROM users')
    await page.getByRole('button', { name: /execute/i }).click()

    await expect(page.getByRole('table')).toBeVisible()

    // Open history panel
    await page.getByRole('button', { name: /history/i }).click()

    // Check history contains the query
    await expect(page.getByTestId('query-history')).toBeVisible()
    await expect(page.getByText('SELECT * FROM users')).toBeVisible()
  })

  test('should handle query errors gracefully', async ({ page }) => {
    const invalidQuery = 'SELEC * FORM users' // Typo

    await page.getByTestId('sql-editor').click()
    await page.keyboard.type(invalidQuery)
    await page.getByRole('button', { name: /execute/i }).click()

    // Should show error message
    await expect(page.getByRole('alert')).toBeVisible()
    await expect(page.getByText(/syntax error/i)).toBeVisible()

    // Should have retry button
    await expect(page.getByRole('button', { name: /retry/i })).toBeVisible()
  })

  test('should be keyboard accessible', async ({ page }) => {
    // Focus on editor
    await page.keyboard.press('Tab')
    await expect(page.getByTestId('sql-editor')).toBeFocused()

    // Type query with keyboard
    await page.keyboard.type('SELECT * FROM users')

    // Tab to execute button
    await page.keyboard.press('Tab')
    await expect(page.getByRole('button', { name: /execute/i })).toBeFocused()

    // Execute with Enter
    await page.keyboard.press('Enter')

    await expect(page.getByRole('table')).toBeVisible()
  })

  test('should work on mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 }) // iPhone size

    // Check mobile layout
    await expect(page.getByTestId('sql-editor')).toBeVisible()
    await expect(page.getByRole('button', { name: /execute/i })).toBeVisible()

    // Execute query
    await page.getByTestId('sql-editor').click()
    await page.keyboard.type('SELECT * FROM users LIMIT 5')
    await page.getByRole('button', { name: /execute/i }).click()

    // Results should be visible
    await expect(page.getByTestId('query-results')).toBeVisible()
  })
})
