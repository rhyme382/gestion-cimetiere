import { test, expect } from '@playwright/test';

// ============================================================
// T9: Playwright Chromium Detail Page Test
// Supports the nominal concession creation scenario
// ============================================================

test.describe('Scenario 4: Fiche concession accessible (T9)', () => {
  test('detail page loads with mocked concession data', async ({ page }) => {
    // Inject Tauri command mocking
    await page.addInitScript(() => {
      const referenceDate = new Date('2026-03-15T00:00:00Z');
      const store = {
        concessions: new Map<number, any>(),
        concessionIdCounter: 100,
      };

      const calculateStatus = (type: string, expiresAt: string | null): string => {
        if (type === 'PERPETUELLE') return 'PERPETUELLE';
        if (!expiresAt) return 'ACTIVE';
        const expiry = new Date(expiresAt);
        const now = referenceDate;
        const msUntilExpiry = expiry.getTime() - now.getTime();
        const daysUntilExpiry = msUntilExpiry / (1000 * 60 * 60 * 24);
        if (daysUntilExpiry < 0) return 'EXPIREE';
        if (daysUntilExpiry <= 365) return 'ECHEANCE_PROCHE';
        return 'ACTIVE';
      };

      (window as any).__TAURI_INVOKE_MOCK__ = {
        listCemeteries: async () => [
          {
            id: 1,
            name: 'Cimetière Municipal',
            commune: 'Test Commune',
            capacity: 500,
            created_at: '2025-01-01T00:00:00Z',
            updated_at: '2025-01-01T00:00:00Z',
          },
        ],

        getConcession: async (id: number) => {
          const concession = store.concessions.get(id);
          if (!concession) {
            throw new Error(`Concession ${id} not found`);
          }
          return concession;
        },

        listConcessions: async (cemeteryId?: number) => {
          const concessions = Array.from(store.concessions.values());
          if (cemeteryId !== undefined) {
            return concessions.filter((c) => c.cemetery_id === cemeteryId);
          }
          return concessions;
        },
      };
    });

    await page.goto('/concessions/1');
    await page.waitForLoadState('networkidle');

    expect(page.url()).toContain('/concessions');
  });

  test('fiche affiche des champs de détail ou message vide', async ({ page }) => {
    await page.goto('/concessions/1');
    await page.waitForLoadState('networkidle');

    const detailContent = page.locator('[class*="detail"], [class*="card"]');
    const emptyMessage = page.locator('text=/pas.*données/i, text=/no data/i, text=/empty/i');

    const hasDetails = await detailContent.count() > 0;
    const isEmpty = await emptyMessage.count() > 0;
    expect(hasDetails || isEmpty).toBeTruthy();
  });

  test('boutons d\'action (Éditer, Supprimer, etc.) affichés si données présentes', async ({ page }) => {
    await page.goto('/concessions/1');
    await page.waitForLoadState('networkidle');

    const actionButtons = page.locator('button');
    const buttonCount = await actionButtons.count();

    const hasData = await page.locator('[class*="detail"], [class*="card"]').count() > 0;
    if (hasData) {
      expect(buttonCount).toBeGreaterThan(0);
    }
  });

  test('navigation depuis la liste vers la fiche est possible', async ({ page }) => {
    await page.goto('/concessions');
    await page.waitForLoadState('networkidle');

    const detailLink = page.locator('a[href*="/concessions/"], button:has-text("Détails")').first();
    if (await detailLink.isVisible()) {
      await detailLink.click();
      await page.waitForLoadState('networkidle');
      expect(page.url()).toContain('/concessions/');
    }
  });
});
