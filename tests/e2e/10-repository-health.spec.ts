import { expect, test } from '@playwright/test';

const nominalDiagnostic = {
  health: 'Ok',
  sqlite_available: true,
  app_version: '1.0.0-e2e',
  message: 'Tout fonctionne normalement',
};

test.describe('Scenario 10: Diagnostic technique dans Paramètres', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript((diagnostic) => {
      const tauriInternals = {
        invoke: async (cmd: string) => {
          if (cmd === 'get_diagnostic') {
            return diagnostic;
          }

          throw new Error(`Unexpected Tauri command in E2E test: ${cmd}`);
        },
        transformCallback: () => 1,
        unregisterCallback: () => {},
      };

      Object.defineProperty(window, '__TAURI_INTERNALS__', {
        value: tauriInternals,
        configurable: true,
      });
    }, nominalDiagnostic);
  });

  test('affiche le diagnostic nominal sur /parametres', async ({ page }) => {
    await page.goto('/parametres');

    const diagnosticTitle = page.getByText('Diagnostic technique');
    await expect(diagnosticTitle).toBeVisible();

    await expect(page.getByText('État global')).toBeVisible();
    await expect(page.getByText(nominalDiagnostic.health, { exact: true })).toBeVisible();

    await expect(page.getByText('Base de données')).toBeVisible();
    await expect(page.getByText('SQLite OK', { exact: true })).toBeVisible();

    await expect(page.getByText('Version', { exact: true })).toBeVisible();
    await expect(page.getByText(nominalDiagnostic.app_version, { exact: true })).toBeVisible();

    await expect(page.getByText('Message', { exact: true })).toBeVisible();
    await expect(page.getByText(nominalDiagnostic.message, { exact: true })).toBeVisible();

    await expect(page.locator('[class*="animate-spin"], [class*="spinner"]')).toHaveCount(0);
  });
});
