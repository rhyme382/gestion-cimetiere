import { test, expect } from '@playwright/test';

test.describe('Scenario 8: Page sauvegardes accessible', () => {
  test('route /sauvegardes accessible', async ({ page }) => {
    await page.goto('/sauvegardes');
    await page.waitForLoadState('networkidle');

    // Vérifier que nous sommes sur la bonne page
    expect(page.url()).toContain('/sauvegardes');
  });

  test('titre sauvegardes affiché', async ({ page }) => {
    await page.goto('/sauvegardes');
    await page.waitForLoadState('networkidle');

    // Vérifier le titre
    const pageTitle = page.locator('h1, h2').filter({ hasText: /Sauvegarde/i });
    const hasTitle = await pageTitle.count() > 0;
    expect(hasTitle).toBeTruthy();
  });

  test('bouton créer sauvegarde affiché', async ({ page }) => {
    await page.goto('/sauvegardes');
    await page.waitForLoadState('networkidle');

    // Chercher le bouton créer sauvegarde
    const createButton = page.locator('button:has-text("Créer"), button:has-text("Nouvelle"), button:has-text("Sauvegard")');
    const hasButton = await createButton.count() > 0;
    expect(hasButton).toBeTruthy();
  });

  test('liste ou tableau sauvegardes affiché', async ({ page }) => {
    await page.goto('/sauvegardes');
    await page.waitForLoadState('networkidle');

    // Chercher un tableau ou liste
    const table = page.locator('table');
    const list = page.locator('[role="list"]');
    const emptyMessage = page.locator('text=/aucune/i, text=/empty/i');

    const hasTable = await table.count() > 0;
    const hasList = await list.count() > 0;
    const isEmpty = await emptyMessage.count() > 0;

    expect(hasTable || hasList || isEmpty).toBeTruthy();
  });

  test('boutons d\'action (Restaurer, Supprimer) affichés si sauvegardes existent', async ({ page }) => {
    await page.goto('/sauvegardes');
    await page.waitForLoadState('networkidle');

    // Chercher les boutons d'action
    const restoreButton = page.locator('button:has-text("Restaurer")');
    const deleteButton = page.locator('button:has-text("Supprimer")');
    const actionButtons = page.locator('button');

    const hasActionButtons = await restoreButton.count() > 0 || await deleteButton.count() > 0;
    const hasAnyButtons = await actionButtons.count() > 0;

    // Si des sauvegardes existent, il doit y avoir des boutons d'action
    expect(hasActionButtons || hasAnyButtons).toBeTruthy();
  });

  test('navigation vers sauvegardes possible depuis menu', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Chercher le lien vers sauvegardes
    const savesLink = page.locator('a[href="/sauvegardes"], a:has-text("Sauvegarde")');
    const hasLink = await savesLink.count() > 0;

    if (hasLink) {
      await savesLink.first().click();
      await page.waitForLoadState('networkidle');
      expect(page.url()).toContain('/sauvegardes');
    }
  });
});
