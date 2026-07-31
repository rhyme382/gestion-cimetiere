import { expect, test, type Page } from "@playwright/test";

async function installConcessionTauriHarness(page: Page): Promise<void> {
  await page.addInitScript(() => {
    const referenceDate = new Date("2026-03-15T00:00:00Z");

    const cemeteries = [
      {
        id: 1,
        name: "Cimetière Municipal E2E",
        commune: "Commune E2E",
        capacity: 500,
        created_at: "2025-01-01T00:00:00Z",
        updated_at: "2025-01-01T00:00:00Z",
      },
    ];

    const plots = [
      {
        id: 1,
        cemetery_id: 1,
        section: "A",
        row: 1,
        number: 1,
        capacity: 1,
        capacity_used: 0,
        occupied_count: 0,
        concession_count: 0,
        status: "available",
        created_at: "2025-01-01T00:00:00Z",
        updated_at: "2025-01-01T00:00:00Z",
      },
    ];

    const store = {
      concessions: new Map<number, Record<string, unknown>>(),
      nextConcessionId: 100,
    };

    const calculateExpirationDate = (
      startDate: string,
      durationYears: number,
    ): string => {
      const start = new Date(`${startDate}T00:00:00Z`);
      const expiry = new Date(start);
      expiry.setUTCFullYear(expiry.getUTCFullYear() + durationYears);

      return expiry.toISOString().slice(0, 10);
    };

    const calculateStatus = (
      concessionType: string,
      expirationDate: string | null,
    ): string => {
      if (concessionType === "PERPETUELLE") {
        return "PERPETUELLE";
      }

      if (!expirationDate) {
        return "ACTIVE";
      }

      const expiration = new Date(`${expirationDate}T00:00:00Z`);
      const millisecondsRemaining =
        expiration.getTime() - referenceDate.getTime();

      const daysRemaining =
        millisecondsRemaining / (1000 * 60 * 60 * 24);

      if (daysRemaining < 0) {
        return "EXPIREE";
      }

      if (daysRemaining <= 365) {
        return "ECHEANCE_PROCHE";
      }

      return "ACTIVE";
    };

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
            return plots.filter(
              (plot) => plot.cemetery_id === args.cemetery_id,
            );

          case "get_plot": {
            const plot = plots.find((item) => item.id === args.id);

            if (!plot) {
              throw new Error(`Plot ${args.id} not found`);
            }

            return plot;
          }

          case "create_concession": {
            const req = args.req;

            if (!req) {
              throw new Error("create_concession requires args.req");
            }

            if (!req.concession_number) {
              throw new Error("Concession number is required");
            }

            const duplicate = Array.from(
              store.concessions.values(),
            ).some(
              (item) =>
                item.concession_number === req.concession_number,
            );

            if (duplicate) {
              throw new Error("Concession number already exists");
            }

            let durationYears: number | null =
              req.duration_years ?? null;

            let expirationDate: string | null = null;

            if (req.concession_type === "TRENTENAIRE") {
              durationYears = 30;
              expirationDate = calculateExpirationDate(
                req.start_date,
                30,
              );
            } else if (
              req.concession_type === "CINQUANTENAIRE"
            ) {
              durationYears = 50;
              expirationDate = calculateExpirationDate(
                req.start_date,
                50,
              );
            } else if (
              req.concession_type === "TEMPORAIRE" &&
              req.duration_years
            ) {
              durationYears = req.duration_years;
              expirationDate = calculateExpirationDate(
                req.start_date,
                req.duration_years,
              );
            }

            const id = store.nextConcessionId++;

            const concession = {
              id,
              cemetery_id: req.cemetery_id,
              plot_id: req.plot_id,
              concession_number: req.concession_number,
              concession_type: req.concession_type,
              duration_years: durationYears,
              start_date: req.start_date,
              end_date: expirationDate,
              expires_at: expirationDate,
              holder_first_name:
                req.holder_first_name ?? null,
              holder_last_name:
                req.holder_last_name ?? null,
              holder_address: req.holder_address ?? null,
              holder_postal_code:
                req.holder_postal_code ?? null,
              holder_commune: req.holder_commune ?? null,
              observations: req.observations ?? null,
              acquired_at: req.acquired_at ?? null,
              renewed_at: null,
              status: calculateStatus(
                req.concession_type,
                expirationDate,
              ),
              created_at: referenceDate.toISOString(),
              updated_at: referenceDate.toISOString(),
            };

            store.concessions.set(id, concession);

            return concession;
          }

          case "get_concession": {
            const concession = store.concessions.get(args.id);

            if (!concession) {
              throw new Error(
                `Concession ${args.id} not found`,
              );
            }

            return concession;
          }

          case "list_concessions": {
            const concessions = Array.from(
              store.concessions.values(),
            );

            if (args.cemetery_id !== undefined) {
              return concessions.filter(
                (item) =>
                  item.cemetery_id === args.cemetery_id,
              );
            }

            return concessions;
          }

          default:
            throw new Error(
              `Unexpected Tauri command in T9: ${command}`,
            );
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

test.describe(
  "Scenario 3: Parcours nominal de création de concession (T9)",
  () => {
    test.beforeEach(async ({ page }) => {
      await installConcessionTauriHarness(page);
    });

    test(
      "Step 1-12: créer une concession trentenaire et vérifier tous les détails",
      async ({ page }) => {
        const concessionNumber = "CON-2026-001";
        const firstName = "Jean";
        const lastName = "Dupont";
        const startDate = "2026-03-15";

        // Étape 1 : ouvrir la liste.
        await page.goto("/concessions");

        await expect(
          page.getByRole("heading", {
            name: "Concessions",
            level: 1,
          }),
        ).toBeVisible();

        // Étape 2 : lancer la création.
        await page
          .getByRole("button", { name: "Créer", exact: true })
          .click();

        await expect(page).toHaveURL(/\/concessions\/new$/);

        // Étape 3 : vérifier le formulaire.
        await expect(
          page.locator("#concession_number"),
        ).toBeVisible();

        // Étape 4 : choisir le cimetière.
        await page
          .locator("#cemetery_id")
          .selectOption("1");

        // Étape 5 : choisir l'emplacement.
        await expect(
          page.locator('#plot_id option[value="1"]'),
        ).toHaveCount(1);

        await page.locator("#plot_id").selectOption("1");

        // Étape 6 : saisir le numéro.
        await page
          .locator("#concession_number")
          .fill(concessionNumber);

        // Étape 7 : choisir le type.
        await page
          .locator("#concession_type")
          .selectOption("TRENTENAIRE");

        // Étape 8 : saisir la date de début.
        await page.locator("#start_date").fill(startDate);

        // Étape 9 : saisir le concessionnaire.
        await page
          .locator("#holder_first_name")
          .fill(firstName);

        await page
          .locator("#holder_last_name")
          .fill(lastName);

        // Étape 10 : créer la concession.
        await page
          .getByRole("button", {
            name: /créer|enregistrer|valider/i,
          })
          .click();

        await expect(page).toHaveURL(
          /\/concessions\/100$/,
        );

        // Étape 11 : vérifier la fiche détail.
        await expect(
          page.getByText(concessionNumber, { exact: true }),
        ).toBeVisible();

        await expect(
          page.getByText(firstName, { exact: true }),
        ).toBeVisible();

        await expect(
          page.getByText(lastName, { exact: true }),
        ).toBeVisible();

        await expect(
          page.getByText(/trentenaire|30 ans/i),
        ).toBeVisible();

        await expect(
          page.getByText(/15\/03\/2056|2056-03-15/),
        ).toBeVisible();

        await expect(
          page.getByText(/actif/i).first(),
        ).toBeVisible();

        // Étape 12 : retour, recherche et présence en liste.
        await page
          .getByRole("link", {
            name: "Concessions",
            exact: true,
          })
          .click();

        await expect(page).toHaveURL(/\/concessions$/);

        const searchInput = page.getByPlaceholder(
          "Numéro, concessionnaire...",
        );

        await searchInput.fill(concessionNumber);

        const concessionRow = page
          .locator("tbody tr")
          .filter({ hasText: concessionNumber });

        await expect(concessionRow).toHaveCount(1);

        await expect(
          concessionRow.getByText(concessionNumber, {
            exact: true,
          }),
        ).toBeVisible();

        await expect(
          concessionRow.getByText(
            `${firstName} ${lastName}`,
            { exact: true },
          ),
        ).toBeVisible();

        await expect(
          concessionRow.getByText(/trentenaire|30 ans/i),
        ).toBeVisible();

        await expect(
          concessionRow.getByText(/actif/i),
        ).toBeVisible();
      },
    );

    test(
      "page concessions affichée avec ses contrôles principaux",
      async ({ page }) => {
        await page.goto("/concessions");

        await expect(
          page.getByRole("heading", {
            name: "Concessions",
            level: 1,
          }),
        ).toBeVisible();

        await expect(
          page.getByPlaceholder(
            "Numéro, concessionnaire...",
          ),
        ).toBeVisible();

        await expect(
          page.getByRole("button", {
            name: "Créer",
            exact: true,
          }),
        ).toBeVisible();
      },
    );

    test(
      "boutons de filtrage affichés",
      async ({ page }) => {
        await page.goto("/concessions");

        for (const label of [
          "Tous",
          "Actif",
          "Échéance proche",
          "Expiré",
          "Perpétuelle",
        ]) {
          await expect(
            page.getByRole("button", {
              name: label,
              exact: true,
            }),
          ).toBeVisible();
        }
      },
    );
  },
);
