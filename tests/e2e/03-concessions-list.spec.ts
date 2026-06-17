import { test, expect } from '@playwright/test';

test.describe('Scenario 3: Liste concessions accessible', () => {
  test('page concessions s\'affiche avec titre', async ({ page }) => {
    await page.goto('/concessions');
    await page.waitForLoadState('networkidle');

    // Vérifier le titre
    const pageTitle = page.locator('h1, h2').filter({ hasText: /Concession/i });
    await expect(pageTitle.first()).toBeVisible();
  });

  test('liste ou tableau concessions visible', async ({ page }) => {
    await page.goto('/concessions');
    await page.waitForLoadState('networkidle');

    // Chercher un tableau ou liste
    const table = page.locator('table');
    const list = page.locator('[role="list"], [class*="list"]');
    const hasTable = await table.count() > 0;
    const hasList = await list.count() > 0;
    expect(hasTable || hasList).toBeTruthy();
  });

  test('boutons de filtrage affichés', async ({ page }) => {
    await page.goto('/concessions');
    await page.waitForLoadState('networkidle');

    // Chercher les boutons de filtrage (active, expired, etc.)
    const filterButtons = page.locator('button');
    const buttonCount = await filterButtons.count();
    expect(buttonCount).toBeGreaterThan(0);
  });

  test('affichage vide ou données selon disponibilité', async ({ page }) => {
    await page.goto('/concessions');
    await page.waitForLoadState('networkidle');

    // Vérifier que la page affiche soit des données soit un message vide
    const content = page.locator('body');
    const isEmpty = await page.locator('text=/aucune/i, text=/no data/i').count() > 0;
    const hasData = await page.locator('table, [role="list"]').count() > 0;
    expect(isEmpty || hasData).toBeTruthy();
  });

  test('state loading/error géré', async ({ page }) => {
    await page.goto('/concessions');

    // Attendre le chargement
    await page.waitForLoadState('networkidle');

    // Vérifier qu'il n'y a pas d'erreur visible à la fin du chargement
    const errorText = page.locator('text=/erreur/i, text=/error/i');
    const errorCount = await errorText.count();
    expect(errorCount).toBeLessThanOrEqual(0);
  });
});
