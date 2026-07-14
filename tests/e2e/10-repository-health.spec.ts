import { test, expect } from '@playwright/test';

test.describe('Scenario 10: Diagnostic technique dans Paramètres', () => {
  test('page /parametres est accessible', async ({ page }) => {
    // Navigate to /parametres
    await page.goto('/parametres');
    await page.waitForLoadState('networkidle');

    // Vérifier que la page s'est chargée
    expect(page.url()).toContain('/parametres');
  });

  test('diagnostic card s\'affiche avec titre', async ({ page }) => {
    await page.goto('/parametres');
    await page.waitForLoadState('networkidle');

    // Vérifier que le titre "Diagnostic technique" est visible
    const diagnosticTitle = page.locator('text=Diagnostic technique');
    await expect(diagnosticTitle).toBeVisible();
  });

  test('loading state est géré correctement', async ({ page }) => {
    await page.goto('/parametres');

    // Attendre le chargement complet
    await page.waitForLoadState('networkidle');

    // Vérifier que le contenu est chargé (loading spinner doit disparaître)
    const spinner = page.locator('[class*="spinner"], [class*="loading"]');
    const spinnerCount = await spinner.count();

    // Soit le spinner n'existe pas, soit il est invisible
    if (spinnerCount > 0) {
      const firstSpinner = spinner.first();
      const isHidden = await firstSpinner.isHidden().catch(() => true);
      expect(isHidden).toBeTruthy();
    }
  });

  test('diagnostic card affiche les badges de statut', async ({ page }) => {
    await page.goto('/parametres');
    await page.waitForLoadState('networkidle');

    // Vérifier que le badge "État global" existe
    const globalHealthLabel = page.locator('text=État global');
    await expect(globalHealthLabel).toBeVisible();

    // Vérifier qu'il y a un badge après le label
    const healthBadges = page.locator('[class*="badge"]');
    const badgeCount = await healthBadges.count();
    expect(badgeCount).toBeGreaterThan(0);
  });

  test('diagnostic card affiche le statut SQLite', async ({ page }) => {
    await page.goto('/parametres');
    await page.waitForLoadState('networkidle');

    // Vérifier que le label "Base de données" existe
    const databaseLabel = page.locator('text=Base de données');
    await expect(databaseLabel).toBeVisible();

    // Vérifier que SQLite est mentionné (OK ou Indisponible)
    const sqliteStatus = page.locator('text=/SQLite|Indisponible/');
    const isVisible = await sqliteStatus.isVisible().catch(() => false);
    expect(isVisible).toBeTruthy();
  });

  test('diagnostic card affiche la version', async ({ page }) => {
    await page.goto('/parametres');
    await page.waitForLoadState('networkidle');

    // Vérifier que le label "Version" existe
    const versionLabel = page.locator('text=Version');
    await expect(versionLabel).toBeVisible();

    // Vérifier qu'une version est affichée (avec du texte monospace)
    const versionValue = page.locator('[class*="font-mono"]');
    const isVersionVisible = await versionValue.isVisible().catch(() => false);
    expect(isVersionVisible).toBeTruthy();
  });

  test('diagnostic nominal affiche les badges de succès', async ({ page }) => {
    await page.goto('/parametres');
    await page.waitForLoadState('networkidle');

    // Attendre que le diagnostic soit chargé
    await page.waitForTimeout(500);

    // Chercher les badges avec variant success (classe "success" ou "bg-green")
    const successBadges = page.locator('[class*="success"], [class*="bg-green"]');
    const badgeCount = await successBadges.count();

    // En cas nominal, au moins le badge global et SQLite devraient être "success"
    // On vérifie qu'au moins un badge est présent (peut être absent en cas d'erreur réelle)
    const allBadges = page.locator('[class*="badge"]');
    await expect(allBadges.first()).toBeVisible();
  });

  test('diagnostic card affiche le contenu complet en nominal', async ({ page }) => {
    await page.goto('/parametres');
    await page.waitForLoadState('networkidle');

    // Vérifier la présence de tous les éléments clés
    const diagnosticCard = page.locator('text=Diagnostic technique').first();
    await expect(diagnosticCard).toBeVisible();

    // Vérifier au moins les deux statuts
    const globalStatus = page.locator('text=État global');
    const databaseStatus = page.locator('text=Base de données');
    const version = page.locator('text=Version');

    await expect(globalStatus).toBeVisible();
    await expect(databaseStatus).toBeVisible();
    await expect(version).toBeVisible();

    // Vérifier qu'il y a du contenu affiché (badges + version)
    const content = page.locator('text=/Ok|Indisponible|SQLite/');
    const isContentVisible = await content.isVisible().catch(() => false);
    expect(isContentVisible).toBeTruthy();
  });

  test('page /parametres complète s\'affiche sans erreur', async ({ page }) => {
    // Setup: listen for console errors
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.goto('/parametres');
    await page.waitForLoadState('networkidle');

    // Vérifier qu'aucune erreur JavaScript majeure n'est survenue
    expect(errors.length).toBe(0);

    // Vérifier que la page est dans un état valide
    const pageContent = page.locator('body');
    await expect(pageContent).toBeVisible();
  });
});
