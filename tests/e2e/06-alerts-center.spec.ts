import { test, expect } from '@playwright/test';

test.describe('Scenario 6: Centre d\'alertes visible', () => {
  test('page alertes s\'affiche avec titre', async ({ page }) => {
    await page.goto('/alertes');
    await page.waitForLoadState('networkidle');

    // Vérifier le titre
    const pageTitle = page.locator('h1, h2').filter({ hasText: /Alerte/i });
    await expect(pageTitle.first()).toBeVisible();
  });

  test('tableau alertes ou widget affiché', async ({ page }) => {
    await page.goto('/alertes');
    await page.waitForLoadState('networkidle');

    // Chercher tableau ou widget
    const table = page.locator('table');
    const alertWidget = page.locator('[class*="alert"], [class*="widget"]');

    const hasTable = await table.count() > 0;
    const hasWidget = await alertWidget.count() > 0;
    expect(hasTable || hasWidget).toBeTruthy();
  });

  test('dashboard affiche widget alertes', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // Chercher le widget alertes
    const alertWidget = page.locator('[class*="alert"], text=/Alerte/i');
    const hasAlertWidget = await alertWidget.count() > 0;
    expect(hasAlertWidget).toBeTruthy();
  });

  test('badge ou compteur alertes affiché', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // Chercher un badge de compteur
    const badge = page.locator('[class*="badge"], span:has-text(/[0-9]+/)');
    const hasBadge = await badge.count() > 0;
    expect(hasBadge).toBeTruthy();
  });

  test('lien ou bouton vers page alertes depuis dashboard', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // Chercher un lien vers les alertes
    const alertLink = page.locator('a[href="/alertes"], button:has-text("Voir tous")');
    const hasLink = await alertLink.count() > 0;
    expect(hasLink).toBeTruthy();
  });
});
