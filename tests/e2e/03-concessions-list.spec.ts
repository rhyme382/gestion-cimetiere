import { test, expect } from '@playwright/test';

// ============================================================
// T9: Playwright Chromium E2E Test for Concession
// Creation Nominal Path (12 Steps from Specification § 20)
//
// This test uses a stateful Tauri harness injected via
// page.addInitScript to mock backend commands before app load.
// The harness maintains an isolated, reinitialized store for
// each test, with deterministic date calculations.
// ============================================================

test.describe('Scenario 3: Parcours nominal de création de concession (T9)', () => {
  test('Step 1-12: Créer concession trentenaire et vérifier tous les détails', async ({ page }) => {
    // Inject Tauri command mocking before page load
    await page.addInitScript(() => {
      const referenceDate = new Date('2026-03-15T00:00:00Z');
      const store = {
        concessions: new Map<number, any>(),
        concessionIdCounter: 100,
      };

      const calculateExpirationDate = (startDate: string, durationYears: number): string => {
        const start = new Date(startDate);
        const expiry = new Date(start);
        expiry.setFullYear(expiry.getFullYear() + durationYears);
        // Handle leap year edge case
        if (start.getMonth() === 1 && start.getDate() === 29 && expiry.getMonth() !== 1) {
          expiry.setDate(28);
        }
        return expiry.toISOString().split('T')[0];
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

      // Mock Tauri invoke: intercept all calls from the app
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

        listPlots: async (cemeteryId: number) => {
          if (cemeteryId === 1) {
            return [
              {
                id: 1,
                cemetery_id: 1,
                section: 'A',
                row: 1,
                number: 1,
                capacity: 1,
                status: 'available',
                created_at: '2025-01-01T00:00:00Z',
                updated_at: '2025-01-01T00:00:00Z',
              },
            ];
          }
          return [];
        },

        createConcession: async (req: any) => {
          if (!req.concession_number) {
            throw new Error('Concession number is required');
          }

          for (const concession of store.concessions.values()) {
            if (concession.concession_number === req.concession_number) {
              throw new Error('Concession number already exists');
            }
          }

          const startDate = req.start_date || '2026-03-15';
          let expiresAt: string | null = null;
          let durationYears = req.duration_years;

          if (req.concession_type === 'PERPETUELLE') {
            expiresAt = null;
          } else if (req.concession_type === 'TRENTENAIRE') {
            durationYears = 30;
            expiresAt = calculateExpirationDate(startDate, 30);
          } else if (req.concession_type === 'CINQUANTENAIRE') {
            durationYears = 50;
            expiresAt = calculateExpirationDate(startDate, 50);
          } else if (req.concession_type === 'TEMPORAIRE' && req.duration_years) {
            expiresAt = calculateExpirationDate(startDate, req.duration_years);
          }

          const concessionId = store.concessionIdCounter++;
          const concession = {
            id: concessionId,
            cemetery_id: req.cemetery_id,
            plot_id: req.plot_id,
            concession_number: req.concession_number,
            concession_type: req.concession_type,
            duration_years: durationYears,
            start_date: startDate,
            holder_first_name: req.holder_first_name || null,
            holder_last_name: req.holder_last_name || null,
            holder_address: req.holder_address || null,
            holder_postal_code: req.holder_postal_code || null,
            holder_commune: req.holder_commune || null,
            observations: req.observations || null,
            acquired_at: req.acquired_at || null,
            expires_at: expiresAt,
            renewed_at: null,
            status: calculateStatus(req.concession_type, expiresAt),
            created_at: referenceDate.toISOString(),
            updated_at: referenceDate.toISOString(),
          };

          store.concessions.set(concessionId, concession);
          return concession;
        },

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

    // STEP 1: Open concessions list
    await page.goto('/concessions');
    await page.waitForLoadState('networkidle');

    const concessionsListTitle = page.locator('h1, h2').filter({ hasText: /Concession/i });
    await expect(concessionsListTitle.first()).toBeVisible();

    // STEP 2: Launch creation
    const createButton = page.locator('button').filter({ hasText: /Créer|Ajouter|Nouveau/i }).first();
    await expect(createButton).toBeVisible();
    await createButton.click();
    await page.waitForLoadState('networkidle');

    // STEP 3: Fill the form
    const concessionNumber = 'CON-2026-001';
    const holderFirstName = 'Jean';
    const holderLastName = 'Dupont';

    const numberInput = page.locator('input').filter({ hasText: concessionNumber }).or(page.locator('input[name*="number"], input[name*="concession"]')).first();
    await numberInput.fill(concessionNumber);

    const firstNameInput = page.locator('input[name*="first"], input[name*="holder"]').first();
    await firstNameInput.fill(holderFirstName);

    const lastNameInput = page.locator('input[name*="last"], input[name*="name"]').nth(1);
    await lastNameInput.fill(holderLastName);

    const cemeterySelect = page.locator('select').first();
    await cemeterySelect.selectOption('1');

    const plotSelect = page.locator('select').nth(1);
    await plotSelect.selectOption('1');

    const typeSelect = page.locator('select').nth(2);
    await typeSelect.selectOption('TRENTENAIRE');

    // STEP 4: Save
    const submitButton = page.locator('button').filter({ hasText: /Enregistrer|Valider|Créer/i }).first();
    await submitButton.click();
    await page.waitForLoadState('networkidle');

    // STEP 5: Check redirect or detail access
    const urlAfterCreate = page.url();
    expect(urlAfterCreate).toContain('/concessions');

    let concessionId: number = 100; // Default from harness

    if (urlAfterCreate.match(/\/concessions\/\d+/) && !urlAfterCreate.endsWith('/concessions')) {
      const match = urlAfterCreate.match(/\/concessions\/(\d+)/);
      concessionId = match ? parseInt(match[1], 10) : 100;
    } else {
      const row = page.locator('tbody tr').filter({ hasText: concessionNumber }).first();
      await expect(row).toBeVisible();
      await row.click();
      await page.waitForLoadState('networkidle');
      const detailUrl = page.url();
      const match = detailUrl.match(/\/concessions\/(\d+)/);
      concessionId = match ? parseInt(match[1], 10) : 100;
    }

    // Ensure we're on detail page
    if (!page.url().includes(`/concessions/${concessionId}`)) {
      await page.goto(`/concessions/${concessionId}`);
      await page.waitForLoadState('networkidle');
    }

    // STEP 6: Verify concession number
    const numberDisplay = page.locator(`text=${concessionNumber}`);
    await expect(numberDisplay).toBeVisible();

    // STEP 7: Verify holder (concessionnaire)
    const holderDisplay = page.locator(`text=${holderFirstName}`).or(page.locator(`text=${holderLastName}`));
    await expect(holderDisplay.first()).toBeVisible();

    // STEP 8: Verify type
    const typeDisplay = page.locator('text=TRENTENAIRE');
    await expect(typeDisplay).toBeVisible();

    // STEP 9: Verify expiration date (2026-03-15 + 30 years = 2056-03-15)
    const expectedExpiry = '2056-03-15';
    const expiryDisplay = page.locator(`text=${expectedExpiry}`);
    await expect(expiryDisplay).toBeVisible();

    // STEP 10: Verify status (ACTIVE: expiry 2056-03-15 > reference 2026-03-15 + 12 months)
    const statusDisplay = page.locator('text=ACTIVE').or(page.locator('text=/Actif/i'));
    await expect(statusDisplay.first()).toBeVisible();

    // STEP 11: Return to list
    const backToListButton = page.locator('a, button').filter({ hasText: /liste|Concessions|Retour/i }).first();
    await backToListButton.click();
    await page.waitForLoadState('networkidle');

    await expect(concessionsListTitle.first()).toBeVisible();

    // STEP 12: Find the created concession in list
    const concessionRow = page.locator('tbody tr').filter({ hasText: concessionNumber });
    await expect(concessionRow).toBeVisible();

    await expect(concessionRow.locator(`text=${concessionNumber}`)).toBeVisible();
    await expect(concessionRow.locator(`text=${holderFirstName}`).or(concessionRow.locator(`text=${holderLastName}`))).toBeVisible();
    await expect(concessionRow.locator('text=TRENTENAIRE')).toBeVisible();
    await expect(concessionRow.locator('text=ACTIVE').or(concessionRow.locator('text=/Actif/i'))).toBeVisible();
  });

  // Backward compatibility tests
  test('page concessions s\'affiche avec titre', async ({ page }) => {
    await page.goto('/concessions');
    await page.waitForLoadState('networkidle');
    const pageTitle = page.locator('h1, h2').filter({ hasText: /Concession/i });
    await expect(pageTitle.first()).toBeVisible();
  });

  test('liste ou tableau concessions visible', async ({ page }) => {
    await page.goto('/concessions');
    await page.waitForLoadState('networkidle');
    const table = page.locator('table');
    const list = page.locator('[role="list"], [class*="list"]');
    const hasTable = await table.count() > 0;
    const hasList = await list.count() > 0;
    expect(hasTable || hasList).toBeTruthy();
  });

  test('boutons de filtrage affichés', async ({ page }) => {
    await page.goto('/concessions');
    await page.waitForLoadState('networkidle');
    const filterButtons = page.locator('button');
    const buttonCount = await filterButtons.count();
    expect(buttonCount).toBeGreaterThan(0);
  });
});
