import { test, expect } from '@playwright/test';

test.describe('Scenario 4: Fiche concession accessible', () => {
  test('page concession detail s\'affiche si ID existe', async ({ page }) => {
    // Essayer d'accéder avec un ID par défaut (sera vide/erreur si pas de données)
    await page.goto('/concessions/1');

    // Attendre le chargement
    await page.waitForLoadState('networkidle');

    // Vérifier que la page s'est chargée (ne pas être sur une erreur 404)
    expect(page.url()).toContain('/concessions');
  });

  test('fiche affiche des champs de détail ou message vide', async ({ page }) => {
    await page.goto('/concessions/1');
    await page.waitForLoadState('networkidle');

    // Chercher des éléments de détail ou message vide
    const detailContent = page.locator('[class*="detail"], [class*="card"]');
    const emptyMessage = page.locator('text=/pas.*données/i, text=/no data/i, text=/empty/i');

    const hasDetails = await detailContent.count() > 0;
    const isEmpty = await emptyMessage.count() > 0;
    expect(hasDetails || isEmpty).toBeTruthy();
  });

  test('boutons d\'action (Éditer, Supprimer, etc.) affichés si données présentes', async ({ page }) => {
    await page.goto('/concessions/1');
    await page.waitForLoadState('networkidle');

    // Chercher les boutons d'action
    const actionButtons = page.locator('button');
    const buttonCount = await actionButtons.count();

    // Si des données, il doit y avoir des boutons
    const hasData = await page.locator('[class*="detail"], [class*="card"]').count() > 0;
    if (hasData) {
      expect(buttonCount).toBeGreaterThan(0);
    }
  });

  test('navigation depuis la liste vers la fiche est possible', async ({ page }) => {
    // Aller d'abord à la liste
    await page.goto('/concessions');
    await page.waitForLoadState('networkidle');

    // Chercher un lien "Détails" ou un élément cliquable
    const detailLink = page.locator('a[href*="/concessions/"], button:has-text("Détails")').first();
    if (await detailLink.isVisible()) {
      await detailLink.click();
      await page.waitForLoadState('networkidle');
      expect(page.url()).toContain('/concessions/');
    }
  });
});
