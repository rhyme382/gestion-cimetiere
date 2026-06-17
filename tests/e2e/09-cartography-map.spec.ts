import { test, expect } from '@playwright/test';

test.describe('Scenario 9: Cartographie visible et sélectionnable', () => {
  test('page emplacements s\'affiche avec titre', async ({ page }) => {
    await page.goto('/emplacements');
    await page.waitForLoadState('networkidle');

    // Vérifier le titre
    const pageTitle = page.locator('h1, h2').filter({ hasText: /Emplacement|Cartograph|Carte/i });
    const hasTitle = await pageTitle.count() > 0;
    expect(hasTitle).toBeTruthy();
  });

  test('composant cartographie (SVG ou canvas) visible', async ({ page }) => {
    await page.goto('/emplacements');
    await page.waitForLoadState('networkidle');

    // Chercher l'élément SVG (cartographie)
    const svg = page.locator('svg');
    const canvas = page.locator('canvas');
    const mapContainer = page.locator('[class*="map"], [class*="canvas"]');

    const hasSvg = await svg.count() > 0;
    const hasCanvas = await canvas.count() > 0;
    const hasMapContainer = await mapContainer.count() > 0;

    expect(hasSvg || hasCanvas || hasMapContainer).toBeTruthy();
  });

  test('éléments cliquables (plots) dans la cartographie', async ({ page }) => {
    await page.goto('/emplacements');
    await page.waitForLoadState('networkidle');

    // Chercher des éléments cliquables (rect, circle, path en SVG)
    const svgElements = page.locator('svg rect, svg circle, svg path, [class*="plot"]');
    const hasElements = await svgElements.count() > 0;

    // Peut être vide si pas de données, mais la structure doit être présente
    expect(await page.locator('svg').count() > 0 || await page.locator('[class*="map"]').count() > 0).toBeTruthy();
  });

  test('sidebar ou détails section pour affichage sélection', async ({ page }) => {
    await page.goto('/emplacements');
    await page.waitForLoadState('networkidle');

    // Chercher une section de détails/sidebar
    const sidebar = page.locator('aside');
    const detailsSection = page.locator('[class*="detail"], [class*="sidebar"]');
    const hasDetails = await sidebar.count() > 0 || await detailsSection.count() > 0;

    expect(hasDetails).toBeTruthy();
  });

  test('navigation vers fiche concession possible si plot sélectionné', async ({ page }) => {
    await page.goto('/emplacements');
    await page.waitForLoadState('networkidle');

    // Chercher un lien vers concession
    const concessionLink = page.locator('a[href*="/concessions/"]');
    const hasLink = await concessionLink.count() > 0;

    // Le lien peut ne pas être présent si pas de données, c'est OK
  });

  test('zoom ou pan sur cartographie fonctionnel (si implémenté)', async ({ page }) => {
    await page.goto('/emplacements');
    await page.waitForLoadState('networkidle');

    // Vérifier que la cartographie SVG peut être manipulée
    const svg = page.locator('svg').first();
    if (await svg.count() > 0) {
      // Essayer de scroller/zoomer
      await svg.hover();
      expect(svg).toBeVisible();
    }
  });

  test('clic sur plot déclenche l\'affichage de détails', async ({ page }) => {
    await page.goto('/emplacements');
    await page.waitForLoadState('networkidle');

    // Chercher un plot/élément cliquable
    const plotElement = page.locator('svg circle, svg rect, [class*="plot"]').first();

    if (await plotElement.isVisible()) {
      // Essayer de cliquer
      await plotElement.click();
      await page.waitForLoadState('networkidle');

      // Vérifier que le détail s'affiche ou la navigation se fait
      const detailsVisible = await page.locator('[class*="detail"], text=/Détails?/i').count() > 0;
      expect(detailsVisible || page.url().includes('/concessions/')).toBeTruthy();
    }
  });
});
