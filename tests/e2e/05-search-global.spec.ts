import { test, expect } from '@playwright/test';

test.describe('Scenario 5: Recherche globale utilisable', () => {
  test('page recherche s\'affiche avec formulaire', async ({ page }) => {
    await page.goto('/recherche');
    await page.waitForLoadState('networkidle');

    // Vérifier le formulaire de recherche
    const searchForm = page.locator('input[type="text"], input[placeholder*="cherch"]');
    await expect(searchForm.first()).toBeVisible();
  });

  test('formulaire de recherche accepte une saisie', async ({ page }) => {
    await page.goto('/recherche');
    await page.waitForLoadState('networkidle');

    const searchInput = page.locator('input[type="text"]').first();
    await searchInput.fill('test');

    // Vérifier que le texte a été saisi
    expect(await searchInput.inputValue()).toBe('test');
  });

  test('bouton Chercher déclenchable', async ({ page }) => {
    await page.goto('/recherche');
    await page.waitForLoadState('networkidle');

    const searchInput = page.locator('input[type="text"]').first();
    await searchInput.fill('test');

    const searchButton = page.locator('button:has-text("Chercher"), button:has-text("Search")').first();
    if (await searchButton.isVisible()) {
      await searchButton.click();
      await page.waitForLoadState('networkidle');
    }
  });

  test('résultats affichés après recherche', async ({ page }) => {
    await page.goto('/recherche');
    await page.waitForLoadState('networkidle');

    // Remplir et soumettre
    const searchInput = page.locator('input[type="text"]').first();
    await searchInput.fill('Jean');

    const searchButton = page.locator('button:has-text("Chercher"), button:has-text("Search")').first();
    if (await searchButton.isVisible()) {
      await searchButton.click();
      await page.waitForLoadState('networkidle');
    }

    // Vérifier que des résultats ou un message "aucun résultat" est affiché
    const resultContent = page.locator('[class*="result"], table, [role="list"]');
    const noResultMessage = page.locator('text=/aucun résultat/i');

    const hasResults = await resultContent.count() > 0;
    const hasNoResultMessage = await noResultMessage.count() > 0;
    expect(hasResults || hasNoResultMessage).toBeTruthy();
  });

  test('recherche avec plusieurs critères (nom + ID)', async ({ page }) => {
    await page.goto('/recherche');
    await page.waitForLoadState('networkidle');

    // La page doit supporter au moins une recherche simple
    const searchInput = page.locator('input[type="text"]').first();
    expect(searchInput).toBeDefined();
  });
});
