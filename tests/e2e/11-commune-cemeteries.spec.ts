import { expect, test, type Page } from "@playwright/test";

async function installCommuneCemeteriesTauriHarness(page: Page): Promise<void> {
  await page.addInitScript(() => {
    // Load persisted state from localStorage, or initialize with defaults
    const loadedState = localStorage.getItem("__e2e_global_state");
    const globalState = loadedState
      ? JSON.parse(loadedState)
      : {
          municipalities: [],
          cemeteries: [],
          nextMunicipalityId: 1,
          nextCemeteryId: 1,
        };

    // Convert arrays back to Maps (if loaded from localStorage)
    const municipalitiesMap = new Map<number, Record<string, any>>(
      Array.isArray(globalState.municipalities)
        ? globalState.municipalities
        : Object.entries(globalState.municipalities || {}).map(([k, v]) => [parseInt(k), v])
    );
    const cemeteriesMap = new Map<number, Record<string, any>>(
      Array.isArray(globalState.cemeteries)
        ? globalState.cemeteries
        : Object.entries(globalState.cemeteries || {}).map(([k, v]) => [parseInt(k), v])
    );

    const persistedState = {
      municipalities: municipalitiesMap,
      cemeteries: cemeteriesMap,
      nextMunicipalityId: globalState.nextMunicipalityId || 1,
      nextCemeteryId: globalState.nextCemeteryId || 1,
    };

    // Save current state to localStorage
    const persistState = () => {
      localStorage.setItem(
        "__e2e_global_state",
        JSON.stringify({
          municipalities: Array.from(persistedState.municipalities.entries()),
          cemeteries: Array.from(persistedState.cemeteries.entries()),
          nextMunicipalityId: persistedState.nextMunicipalityId,
          nextCemeteryId: persistedState.nextCemeteryId,
        })
      );
    };

    (window as any).__globalE2EState = persistedState;
    (window as any).__persistE2EState = persistState;

    // Initialize with one municipality if none exist
    if (persistedState.municipalities.size === 0) {
      const defaultMunicipality = {
        id: 1,
        name: "Test Municipality",
        insee_code: "75056",
        postal_code: "75001",
        email: "test@commune.fr",
        department: "75",
        region: "Île-de-France",
        notes: "Test commune",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };

      persistedState.municipalities.set(1, defaultMunicipality);
      persistedState.nextMunicipalityId = 2;
      (window as any).__persistE2EState();
    }

    const tauriInternals = {
      invoke: async (command: string, args: Record<string, any> = {}): Promise<any> => {
        const persist = (window as any).__persistE2EState;
        switch (command) {
          // Municipality commands
          case "list_municipalities": {
            return Array.from(persistedState.municipalities.values());
          }

          case "get_municipality": {
            const municipality = persistedState.municipalities.get(args.id);
            if (!municipality) {
              throw new Error(`Municipality ${args.id} not found`);
            }
            return municipality;
          }

          case "create_municipality": {
            const req = args.req;
            if (!req || !req.name || !req.insee_code) {
              throw new Error("Municipality name and insee_code are required");
            }

            const id = persistedState.nextMunicipalityId++;
            const municipality = {
              id,
              name: req.name,
              insee_code: req.insee_code,
              postal_code: req.postal_code || null,
              email: req.email || null,
              department: req.department || null,
              region: req.region || null,
              notes: req.notes || null,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            };
            persistedState.municipalities.set(id, municipality);
            persist();
            return municipality;
          }

          case "update_municipality": {
            const municipality = persistedState.municipalities.get(args.id);
            if (!municipality) {
              throw new Error(`Municipality ${args.id} not found`);
            }

            const req = args.req;
            const updated = {
              ...municipality,
              ...req,
              id: municipality.id,
              updated_at: new Date().toISOString(),
            };
            persistedState.municipalities.set(args.id, updated);
            persist();
            return updated;
          }

          case "delete_municipality": {
            persistedState.municipalities.delete(args.id);
            persist();
            return undefined;
          }

          // Cemetery commands
          case "list_cemeteries": {
            return Array.from(persistedState.cemeteries.values());
          }

          case "get_cemetery": {
            const cemetery = persistedState.cemeteries.get(args.id);
            if (!cemetery) {
              throw new Error(`Cemetery ${args.id} not found`);
            }
            return cemetery;
          }

          case "create_cemetery": {
            const req = args.req;
            if (!req || !req.name) {
              throw new Error("Cemetery name is required");
            }

            // Validate capacity if provided
            if (req.capacity !== undefined && req.capacity !== null && req.capacity < 0) {
              throw new Error("Capacity must be a positive number");
            }

            // Check for duplicate name (case-insensitive)
            const duplicate = Array.from(persistedState.cemeteries.values()).some(
              (c) => c.name.toLowerCase() === req.name.toLowerCase()
            );
            if (duplicate) {
              throw new Error("Cemetery name already exists");
            }

            const id = persistedState.nextCemeteryId++;
            const cemetery = {
              id,
              name: req.name,
              commune: req.commune || null,
              capacity: req.capacity || null,
              municipality_id: req.municipality_id || null,
              address: req.address || null,
              is_active: 1,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            };
            persistedState.cemeteries.set(id, cemetery);
            persist();
            return cemetery;
          }

          case "update_cemetery": {
            const cemetery = persistedState.cemeteries.get(args.id);
            if (!cemetery) {
              throw new Error(`Cemetery ${args.id} not found`);
            }

            const req = args.req;

            // Validate capacity if provided
            if (req.capacity !== undefined && req.capacity !== null && req.capacity < 0) {
              throw new Error("Capacity must be a positive number");
            }

            const updated = {
              ...cemetery,
              name: req.name !== undefined ? req.name : cemetery.name,
              commune: req.commune !== undefined ? req.commune : cemetery.commune,
              capacity: req.capacity !== undefined ? req.capacity : cemetery.capacity,
              municipality_id: req.municipality_id !== undefined ? req.municipality_id : cemetery.municipality_id,
              address: req.address !== undefined ? req.address : cemetery.address,
              is_active: req.is_active !== undefined ? req.is_active : cemetery.is_active,
              updated_at: new Date().toISOString(),
            };
            persistedState.cemeteries.set(args.id, updated);
            persist();
            return updated;
          }

          case "delete_cemetery": {
            persistedState.cemeteries.delete(args.id);
            persist();
            return undefined;
          }

          // Diagnostic command
          case "get_diagnostic": {
            return {
              health: "Ok",
              sqlite_available: true,
              app_version: "1.0.0-e2e",
              message: "Tout fonctionne normalement",
            };
          }

          default:
            throw new Error(`Unexpected Tauri command in E2E test: ${command}`);
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
}

test.describe("Scenario 11: Configuration commune et gestion des cimetières", () => {
  test.beforeEach(async ({ page }) => {
    await installCommuneCemeteriesTauriHarness(page);
  });

  test("parametres page loads and displays municipality configuration form", async ({ page }) => {
    // Navigate to parametres page
    await page.goto("/parametres");
    await page.waitForLoadState("networkidle");

    // Verify the page title contains "Paramètres"
    const heading = page.getByRole("heading", { name: /Paramètres de l'application/i });
    await expect(heading).toBeVisible();

    // Verify the form fields are present
    const nameInput = page.locator('input[id="name"]');
    await expect(nameInput).toBeVisible();

    const inseeInput = page.locator('input[id="insee_code"]');
    await expect(inseeInput).toBeVisible();

    // Verify initial municipality data is loaded
    const nameValue = await nameInput.inputValue();
    expect(nameValue).toBeTruthy();

    const inseeValue = await inseeInput.inputValue();
    expect(inseeValue).toBeTruthy();
  });

  test("full E2E scenario: configure commune, create two cemeteries, modify one, and verify persistence", async ({ page }) => {
    // ===== STEP 1: Configure the commune =====
    // Navigate to parametres page
    await page.goto("/parametres");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(500);

    // Get the form fields
    const nameInput = page.locator('input[id="name"]');
    const inseeInput = page.locator('input[id="insee_code"]');
    const postalInput = page.locator('input[id="postal_code"]');
    const emailInput = page.locator('input[id="email"]');

    // Update municipality name
    await nameInput.clear();
    await nameInput.fill("Commune de Test");

    // Verify the update is reflected in the input
    let nameValue = await nameInput.inputValue();
    expect(nameValue).toBe("Commune de Test");

    // Update INSEE code
    await inseeInput.clear();
    await inseeInput.fill("12345");

    // Verify the update is reflected in the input
    let inseeValue = await inseeInput.inputValue();
    expect(inseeValue).toBe("12345");

    // Update postal code
    await postalInput.clear();
    await postalInput.fill("75001");

    let postalValue = await postalInput.inputValue();
    expect(postalValue).toBe("75001");

    // Update email
    await emailInput.clear();
    await emailInput.fill("mairie@commune-test.fr");

    let emailValue = await emailInput.inputValue();
    expect(emailValue).toBe("mairie@commune-test.fr");

    // SAVE the municipality configuration
    const saveButton = page.getByRole("button", { name: /Enregistrer/i });
    await expect(saveButton).toBeVisible();
    await saveButton.click();

    // Wait for save to complete (success message or form update)
    await page.waitForTimeout(1000);

    // Verify the saved values are still displayed
    nameValue = await nameInput.inputValue();
    expect(nameValue).toBe("Commune de Test");
    inseeValue = await inseeInput.inputValue();
    expect(inseeValue).toBe("12345");
    postalValue = await postalInput.inputValue();
    expect(postalValue).toBe("75001");
    emailValue = await emailInput.inputValue();
    expect(emailValue).toBe("mairie@commune-test.fr");

    // ===== STEP 2: Navigate to cemeteries page and create first cemetery =====
    await page.goto("/cimetieres");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(500);

    // Verify we're on the cemeteries page
    expect(page.url()).toContain("/cimetieres");

    // Click "Ajouter un cimetière" button to create first cemetery
    const addButton = page.getByRole("button", { name: /Ajouter un cimetière/i });
    await expect(addButton).toBeVisible({ timeout: 5000 });
    await addButton.click();

    // Wait for form to appear
    await page.waitForTimeout(300);

    // Fill in the first cemetery
    let cemeteryNameInput = page.locator('input#cemetery-name');
    await expect(cemeteryNameInput).toBeVisible();
    await cemeteryNameInput.fill("Cimetière du Nord");

    let cemeteryAddressInput = page.locator('input#cemetery-address');
    await cemeteryAddressInput.fill("123 Avenue de la Paix");

    let cemeteryCommune = page.locator('input#cemetery-commune');
    await cemeteryCommune.fill("Commune de Test");

    let cemeteryCapacity = page.locator('input#cemetery-capacity');
    await cemeteryCapacity.fill("500");

    // Submit the form
    let submitButton = page.getByRole("button", { name: /Créer/i });
    await submitButton.click();

    // Wait for form to close and success
    await page.waitForTimeout(1500);

    // Verify the first cemetery appears in the list
    let cemeteryNord = page.getByText("Cimetière du Nord");
    await expect(cemeteryNord).toBeVisible();

    // ===== STEP 3: Create second cemetery =====
    await addButton.click();
    await page.waitForTimeout(300);

    // Fill in the second cemetery
    cemeteryNameInput = page.locator('input#cemetery-name');
    await cemeteryNameInput.fill("Cimetière du Sud");

    cemeteryAddressInput = page.locator('input#cemetery-address');
    await cemeteryAddressInput.fill("456 Rue de Lyon");

    cemeteryCommune = page.locator('input#cemetery-commune');
    await cemeteryCommune.fill("Commune de Test");

    cemeteryCapacity = page.locator('input#cemetery-capacity');
    await cemeteryCapacity.fill("300");

    // Submit the form
    submitButton = page.getByRole("button", { name: /Créer/i });
    await submitButton.click();
    await page.waitForTimeout(1500);

    // Verify both cemeteries are visible
    let cemetierySud = page.getByText("Cimetière du Sud");
    await expect(cemeteryNord).toBeVisible();
    await expect(cemetierySud).toBeVisible();

    // Verify addresses also appear in the list
    await expect(page.getByText("123 Avenue de la Paix")).toBeVisible();
    await expect(page.getByText("456 Rue de Lyon")).toBeVisible();

    // ===== STEP 4: Modify the first cemetery =====
    // Get all edit buttons and click the first one
    const allEditButtons = await page.locator('button[title="Modifier"]').all();
    if (allEditButtons.length > 0) {
      await allEditButtons[0].click();
      await page.waitForTimeout(300);

      // Update the address in edit mode
      const editAddressInput = page.locator('input#cemetery-address');
      await editAddressInput.clear();
      await editAddressInput.fill("123 Avenue de la Paix - Secteur A");

      // Submit the edit
      const editSubmitButton = page.getByRole("button", { name: /Modifier/i });
      await editSubmitButton.click();
      await page.waitForTimeout(1500);

      // Verify the updated address is visible
      await expect(page.getByText("123 Avenue de la Paix - Secteur A")).toBeVisible();
    }

    // ===== STEP 5: Navigate away to parametres page =====
    await page.goto("/parametres");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(500);

    // Verify on parametres page
    expect(page.url()).toContain("/parametres");

    // ===== STEP 6: Navigate back to cemeteries page and verify persistence =====
    await page.goto("/cimetieres");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(500);

    // Verify page is loaded and URL is correct
    expect(page.url()).toContain("/cimetieres");

    // Verify both cemeteries still exist
    await expect(cemeteryNord).toBeVisible();
    await expect(cemetierySud).toBeVisible();

    // Verify the modified address persists
    await expect(page.getByText("123 Avenue de la Paix - Secteur A")).toBeVisible();

    // Verify the second cemetery's address also persists
    await expect(page.getByText("456 Rue de Lyon")).toBeVisible();

    // ===== STEP 7: Verify commune configuration persisted =====
    // Navigate back to parametres to verify commune configuration was persisted
    await page.goto("/parametres");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(500);

    // Verify the saved commune values are still there
    nameValue = await nameInput.inputValue();
    expect(nameValue).toBe("Commune de Test");
    inseeValue = await inseeInput.inputValue();
    expect(inseeValue).toBe("12345");
    postalValue = await postalInput.inputValue();
    expect(postalValue).toBe("75001");
    emailValue = await emailInput.inputValue();
    expect(emailValue).toBe("mairie@commune-test.fr");
  });

  test("municipality configuration form fields can be updated", async ({ page }) => {
    // Navigate to parametres page
    await page.goto("/parametres");
    await page.waitForLoadState("networkidle");

    // Get the form fields
    const nameInput = page.locator('input[id="name"]');
    const inseeInput = page.locator('input[id="insee_code"]');
    const postalInput = page.locator('input[id="postal_code"]');
    const emailInput = page.locator('input[id="email"]');

    // Update municipality name
    await nameInput.clear();
    await nameInput.fill("Saint-Denis");

    // Verify the update is reflected in the input
    let nameValue = await nameInput.inputValue();
    expect(nameValue).toBe("Saint-Denis");

    // Update INSEE code
    await inseeInput.clear();
    await inseeInput.fill("93066");

    // Verify the update is reflected in the input
    let inseeValue = await inseeInput.inputValue();
    expect(inseeValue).toBe("93066");

    // Update postal code
    await postalInput.clear();
    await postalInput.fill("93200");

    let postalValue = await postalInput.inputValue();
    expect(postalValue).toBe("93200");

    // Update email
    await emailInput.clear();
    await emailInput.fill("contact@saint-denis.fr");

    let emailValue = await emailInput.inputValue();
    expect(emailValue).toBe("contact@saint-denis.fr");
  });

  test("parametres page does not display loading spinners when data is loaded", async ({ page }) => {
    // Navigate to parametres page
    await page.goto("/parametres");
    await page.waitForLoadState("networkidle");

    // Wait a moment for data to load
    await page.waitForTimeout(500);

    // Check that there are no loading spinners
    const spinners = page.locator('[class*="animate-spin"], [class*="spinner"]');
    const spinnerCount = await spinners.count();
    expect(spinnerCount).toBe(0);
  });

  test("diagnostic card is visible on parametres page", async ({ page }) => {
    // Navigate to parametres page
    await page.goto("/parametres");
    await page.waitForLoadState("networkidle");

    // Verify diagnostic card appears
    const diagnosticTitle = page.getByText(/Diagnostic technique/i);
    await expect(diagnosticTitle).toBeVisible({ timeout: 5000 });
  });

  test("municipality data persists across form field interactions", async ({ page }) => {
    // Navigate to parametres page
    await page.goto("/parametres");
    await page.waitForLoadState("networkidle");

    // Get the form fields
    const nameInput = page.locator('input[id="name"]');
    const inseeInput = page.locator('input[id="insee_code"]');

    // Store initial values
    const initialNameValue = await nameInput.inputValue();
    const initialInseeValue = await inseeInput.inputValue();

    // Make changes
    await nameInput.clear();
    await nameInput.fill("New Commune Name");

    // Verify the change
    let currentNameValue = await nameInput.inputValue();
    expect(currentNameValue).toBe("New Commune Name");

    // The INSEE code should remain unchanged
    let currentInseeValue = await inseeInput.inputValue();
    expect(currentInseeValue).toBe(initialInseeValue);

    // Update INSEE as well
    await inseeInput.clear();
    await inseeInput.fill("12345");

    // Verify both changes are in place
    currentNameValue = await nameInput.inputValue();
    currentInseeValue = await inseeInput.inputValue();
    expect(currentNameValue).toBe("New Commune Name");
    expect(currentInseeValue).toBe("12345");
  });

  test("parametres page renders without JavaScript errors", async ({ page }) => {
    // Listen for console errors
    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        consoleErrors.push(msg.text());
      }
    });

    // Navigate to parametres page
    await page.goto("/parametres");
    await page.waitForLoadState("networkidle");

    // Wait for page to fully settle
    await page.waitForTimeout(500);

    // Verify there are no critical console errors
    const criticalErrors = consoleErrors.filter((err) => !err.includes("hydration"));
    expect(criticalErrors).toHaveLength(0);

    // Verify essential elements are present
    const heading = page.getByRole("heading", { name: /Paramètres de l'application/i });
    await expect(heading).toBeVisible();
  });

  test("municipality configuration shows all expected form sections", async ({ page }) => {
    // Navigate to parametres page
    await page.goto("/parametres");
    await page.waitForLoadState("networkidle");

    // Verify form sections are present
    const nameLabel = page.getByLabel(/Nom de la commune/i);
    await expect(nameLabel).toBeVisible();

    const inseeLabel = page.getByLabel(/Code INSEE/i);
    await expect(inseeLabel).toBeVisible();

    const postalLabel = page.getByLabel(/Code postal/i);
    await expect(postalLabel).toBeVisible();

    const emailLabel = page.getByLabel(/Adresse e-mail/i);
    await expect(emailLabel).toBeVisible();

    const deptLabel = page.getByLabel(/Département/i);
    await expect(deptLabel).toBeVisible();

    const regionLabel = page.getByLabel(/Région/i);
    await expect(regionLabel).toBeVisible();

    const notesLabel = page.getByLabel(/Notes/i);
    await expect(notesLabel).toBeVisible();

    // Verify submit button
    const submitButton = page.getByRole("button", { name: /Enregistrer/i });
    await expect(submitButton).toBeVisible();
  });

  test("cemeteries page loads successfully", async ({ page }) => {
    // Navigate to cemeteries page
    await page.goto("/cimetieres");
    await page.waitForLoadState("networkidle");

    // Wait a bit for content to render
    await page.waitForTimeout(500);

    // Verify the page is displayed (look for the icon or content)
    const pageContent = page.locator("body");
    await expect(pageContent).toBeVisible();

    // Verify navigation was successful
    expect(page.url()).toContain("/cimetieres");
  });

  test("create and manage cemeteries with mock backend", async ({ page }) => {
    // Navigate to cemeteries page
    await page.goto("/cimetieres");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(500);

    // Click "Ajouter un cimetière" button to create first cemetery
    const addButton = page.getByRole("button", { name: /Ajouter un cimetière/i });
    await expect(addButton).toBeVisible({ timeout: 5000 });
    await addButton.click();

    // Wait for form to appear
    await page.waitForTimeout(300);

    // Fill in the first cemetery
    const nameInput = page.locator('input#cemetery-name');
    await expect(nameInput).toBeVisible();
    await nameInput.fill("Cimetière du Nord");

    const addressInput = page.locator('input#cemetery-address');
    await addressInput.fill("123 Avenue de la Paix");

    const communeInput = page.locator('input#cemetery-commune');
    await communeInput.fill("Paris");

    const capacityInput = page.locator('input#cemetery-capacity');
    await capacityInput.fill("500");

    // Submit the form
    const submitButton = page.getByRole("button", { name: /Créer/i });
    await submitButton.click();

    // Wait for form to close and success message
    await page.waitForTimeout(1500);

    // Verify the first cemetery appears in the list
    const cemeteryNord = page.getByText("Cimetière du Nord");
    await expect(cemeteryNord).toBeVisible();

    // Now create a second cemetery
    await addButton.click();
    await page.waitForTimeout(300);

    // Fill in the second cemetery
    await nameInput.fill("Cimetière du Sud");
    await addressInput.fill("456 Rue de Lyon");
    await communeInput.fill("Paris");
    await capacityInput.fill("300");

    // Submit the form
    await submitButton.click();
    await page.waitForTimeout(1500);

    // Verify both cemeteries are visible
    const cemetierySud = page.getByText("Cimetière du Sud");
    await expect(cemeteryNord).toBeVisible();
    await expect(cemetierySud).toBeVisible();

    // Verify addresses also appear in the list
    await expect(page.getByText("123 Avenue de la Paix")).toBeVisible();
    await expect(page.getByText("456 Rue de Lyon")).toBeVisible();
  });

  test("cemetery persistence across navigation", async ({ page }) => {
    // Navigate to cemeteries page
    await page.goto("/cimetieres");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(500);

    // Verify page is loaded
    expect(page.url()).toContain("/cimetieres");

    // Create first cemetery
    const addButton = page.getByRole("button", { name: /Ajouter un cimetière/i });
    await expect(addButton).toBeVisible({ timeout: 5000 });
    await addButton.click();
    await page.waitForTimeout(300);

    // Fill and submit first cemetery
    const nameInput = page.locator('input#cemetery-name');
    await nameInput.fill("Cimetière de Persistance 1");

    const addressInput = page.locator('input#cemetery-address');
    await addressInput.fill("100 Rue de la Paix");

    const communeInput = page.locator('input#cemetery-commune');
    await communeInput.fill("Lyon");

    const submitButton = page.getByRole("button", { name: /Créer/i });
    await submitButton.click();
    await page.waitForTimeout(1500);

    // Verify first cemetery created
    const test1 = page.getByText("Cimetière de Persistance 1");
    await expect(test1).toBeVisible();

    // Create second cemetery
    await addButton.click();
    await page.waitForTimeout(300);

    await nameInput.fill("Cimetière de Persistance 2");
    await addressInput.fill("200 Rue de la Paix");
    await communeInput.fill("Lyon");

    await submitButton.click();
    await page.waitForTimeout(1500);

    // Verify both cemeteries exist
    const test2 = page.getByText("Cimetière de Persistance 2");
    await expect(test1).toBeVisible();
    await expect(test2).toBeVisible();

    // Edit first cemetery to add more info to the address
    // Get all edit buttons and click the first one
    const allEditButtons = await page.locator('button[title="Modifier"]').all();
    if (allEditButtons.length > 0) {
      await allEditButtons[0].click();
      await page.waitForTimeout(300);

      // Update the address in edit mode
      const editAddressInput = page.locator('input#cemetery-address');
      await editAddressInput.clear();
      await editAddressInput.fill("100 Rue de la Paix - Secteur A");

      // Submit the edit
      const editSubmitButton = page.getByRole("button", { name: /Modifier/i });
      await editSubmitButton.click();
      await page.waitForTimeout(1500);

      // Verify the updated address is visible
      await expect(page.getByText("100 Rue de la Paix - Secteur A")).toBeVisible();
    }

    // Navigate away to parametres
    await page.goto("/parametres");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(500);

    // Verify on parametres page
    expect(page.url()).toContain("/parametres");

    // Navigate back to cemeteries
    await page.goto("/cimetieres");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(500);

    // Verify page is loaded and data persists
    expect(page.url()).toContain("/cimetieres");

    // Verify both cemeteries still exist
    await expect(test1).toBeVisible();
    await expect(test2).toBeVisible();

    // Verify the modified address persists
    await expect(page.getByText("100 Rue de la Paix - Secteur A")).toBeVisible();

    // Verify the second cemetery's address also persists
    await expect(page.getByText("200 Rue de la Paix")).toBeVisible();
  });
});
