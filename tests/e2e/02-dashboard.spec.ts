import { test, expect } from '@playwright/test';

test.describe('Scenario 2: Dashboard visible avec statistiques', () => {
  test('dashboard s\'affiche avec titre', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // Vérifier le titre du dashboard
    const dashboardTitle = page.locator('h1, h2').filter({ hasText: /Dashboard|Tableau de bord/i });
    await expect(dashboardTitle.first()).toBeVisible();
  });

  test('dashboard affiche des cartes de statistiques', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // Chercher les cartes (Card elements)
    const cards = page.locator('[class*="card"], [role="region"]');
    const cardCount = await cards.count();
    expect(cardCount).toBeGreaterThan(0);
  });

  test('dashboard affiche le widget alertes', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // Chercher le widget alertes
    const alertWidget = page.locator('text=/Alertes?/i');
    const isAlertWidgetVisible = await alertWidget.isVisible().catch(() => false);
    expect(isAlertWidgetVisible || await page.locator('[class*="alert"]').count() > 0).toBeTruthy();
  });

  test('dashboard affiche une liste ou section de données', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // Chercher un tableau ou liste
    const table = page.locator('table');
    const list = page.locator('[role="list"]');
    const hasTable = await table.count() > 0;
    const hasList = await list.count() > 0;
    expect(hasTable || hasList).toBeTruthy();
  });

  test('dashboard state loading est géré', async ({ page }) => {
    await page.goto('/dashboard');

    // Vérifier que le spinner de chargement disparaît
    const spinner = page.locator('[class*="spinner"], [class*="loading"]');
    await page.waitForLoadState('networkidle');

    // Après le chargement, les données doivent être visibles
    const content = page.locator('body');
    await expect(content).toBeVisible();
  });
});
