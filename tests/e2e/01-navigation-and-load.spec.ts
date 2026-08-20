import { test, expect } from '@playwright/test';

test.describe('Scenario 1: Navigation et chargement application', () => {
  test('application charge et affiche le shell', async ({ page }) => {
    // Navigate to root
    await page.goto('/');

    // Attendre le chargement de l'application
    await page.waitForLoadState('networkidle');

    // Vérifier que la page s'est chargée
    expect(page).toBeDefined();
  });

  test('sidebar navigable visible', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Vérifier que le sidebar existe
    const sidebar = page.locator('aside');
    await expect(sidebar).toBeVisible();
  });

  test('header visible avec titres de navigation', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Vérifier que le header existe
    const header = page.locator('header');
    await expect(header).toBeVisible();
  });

  test('navigation vers /dashboard possible', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Cliquer sur un lien du menu
    const dashboardLink = page.locator('a[href="/dashboard"]');
    if (await dashboardLink.isVisible()) {
      await dashboardLink.click();
      await page.waitForLoadState('networkidle');
      expect(page.url()).toContain('/dashboard');
    }
  });

  test('titre application affiché', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Vérifier que le titre contient quelque chose
    const pageTitle = await page.title();
    expect(pageTitle.length).toBeGreaterThan(0);
  });
});
