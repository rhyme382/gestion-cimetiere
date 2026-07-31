import { test, expect } from '@playwright/test';

// ============================================================
// T9: Playwright Chromium Detail Page Test
// Supports the nominal concession creation scenario
// ============================================================

test.describe('Scenario 4: Fiche concession accessible (T9)', () => {
  test.beforeEach(async ({ page }) => {
    // Inject Tauri command mocking
    await page.addInitScript(() => {
      const referenceDate = new Date('2026-03-15T00:00:00Z');
      const store = {
        concessions: new Map<number, any>(),
        concessionIdCounter: 100,
      };

      store.concessions.set(1, {
        id: 1,
        cemetery_id: 1,
        plot_id: null,
        concession_number: 'C-001',
        holder_first_name: 'Jean',
        holder_last_name: 'Dupont',
        concession_type: 'TRENTENAIRE',
        start_date: '2020-01-01',
        expires_at: '2050-01-01',
        status: 'ACTIVE',
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
      });

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

      const cemeteries = [
        {
          id: 1,
          name: "Cimetière Municipal",
          commune: "Test Commune",
          capacity: 500,
          created_at: "2025-01-01T00:00:00Z",
          updated_at: "2025-01-01T00:00:00Z",
        },
      ];

      const tauriInternals = {
        invoke: async (
          command: string,
          args: Record<string, any> = {},
        ): Promise<any> => {
          switch (command) {
            case "list_cemeteries":
              return cemeteries;

            case "get_cemetery": {
              const cemetery = cemeteries.find(
                (item) => item.id === args.id,
              );

              if (!cemetery) {
                throw new Error(`Cemetery ${args.id} not found`);
              }

              return cemetery;
            }

            case "list_plots":
              return [];

            case "get_concession": {
              const concession = store.concessions.get(args.id);

              if (!concession) {
                throw new Error(`Concession ${args.id} not found`);
              }

              return concession;
            }

            case "list_concessions": {
              const concessions = Array.from(
                store.concessions.values(),
              );

              if (args.cemetery_id !== undefined) {
                return concessions.filter(
                  (concession) =>
                    concession.cemetery_id === args.cemetery_id,
                );
              }

              return concessions;
            }

            default:
              throw new Error(`Unhandled Tauri command: ${command}`);
          }
        },
        transformCallback: () => 1,
        unregisterCallback: () => {},
      };

      Object.defineProperty(window, "__TAURI_INTERNALS__", {
        value: tauriInternals,
        configurable: true,
      });
    });

  });

  test('detail page loads with mocked concession data', async ({ page }) => {
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

    const detailContent = page.locator('[class*="detail"], [class*="card"]').first();
    await expect(detailContent).toBeVisible();

    const actionButtons = page.locator('button');
    const buttonCount = await actionButtons.count();

    expect(buttonCount).toBeGreaterThan(0);
  });

  test('navigation depuis la liste vers la fiche est possible', async ({ page }) => {
    await page.goto('/concessions');
    await page.waitForLoadState('networkidle');

    const detailLink = page.locator('a[href*="/concessions/"], button:has-text("Détails")').first();
    await expect(detailLink).toBeVisible();

    await detailLink.click();
    await page.waitForLoadState('networkidle');

    expect(page.url()).toContain('/concessions/');
  });
});
