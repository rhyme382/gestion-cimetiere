# Conventions QA du MVP

Date : 2026-06-15
Domaine : Validation et tests

## Nomenclature et organisation des tests

### Structure des répertoires

```
tests/
├── unit/                          # Tests unitaires
│   ├── backend/                   # Rust + backend logic
│   │   ├── entities/              # Schéma, migrations
│   │   ├── business/              # Règles métier
│   │   └── commands/              # Commandes Tauri
│   └── frontend/                  # TypeScript + React
│       ├── components/            # Composants UI
│       ├── hooks/                 # Custom hooks
│       └── utils/                 # Fonctions utilitaires
├── integration/                   # Tests d'intégration
│   ├── backend/
│   │   ├── database/              # Contrats Tauri + SQLite
│   │   └── api/                   # Endpoint validation
│   └── frontend/
│       └── api-calls/             # Intégration Tauri-React
├── e2e/                           # Tests end-to-end
│   ├── flows/
│   │   ├── concessions.spec.ts
│   │   ├── defunts.spec.ts
│   │   ├── search.spec.ts
│   │   ├── alerts.spec.ts
│   │   ├── cartography.spec.ts
│   │   └── installation.spec.ts
│   └── fixtures/                  # Données de test
├── fixtures/                      # Données partagées
│   ├── init_mvp.sql               # Base de test standard
│   ├── seed-concessions.json
│   └── seed-defunts.json
└── reports/                       # Résultats de test
    ├── unit-results.json
    ├── integration-results.json
    └── e2e-results.json
```

### Nomenclature des fichiers de test

#### Tests unitaires

Format : `<domaine>.<entité>.test.ts` ou `<fonction>.test.rs`

Exemples :
- `backend/entities/schema.test.ts` (migrations) ;
- `backend/business/alert_calculation.test.ts` (alertes) ;
- `frontend/components/ConcessionForm.test.tsx` (composant) ;
- `frontend/hooks/useConcession.test.ts` (hook).

#### Tests d'intégration

Format : `<flux>.integration.test.ts`

Exemples :
- `backend/database/create_concession.integration.test.ts` ;
- `frontend/api-calls/tauri_commands.integration.test.ts`.

#### Tests E2E

Format : `<flux_critique>.spec.ts`

Exemples :
- `e2e/flows/concessions.spec.ts` ;
- `e2e/flows/search.spec.ts`.

### Nomenclature des identifiants de test

Chaque test automatisé reçoit un identifiant unique pour tracabilité :

Format : `T-<domaine>-<numéro>`

Domaines :
- `T-SCHEMA` : schéma et migrations ;
- `T-CIMETIÈRE` : cimetières et sections ;
- `T-EMPLACEMENT` : emplacements et cartographie ;
- `T-CONCESSION` : concessions ;
- `T-PERSONNE` : personnes et défunts ;
- `T-RECHERCHE` : recherche globale ;
- `T-ALERTE` : alertes d'échéance ;
- `T-INSTALL` : installation packaging.

Exemples :
- `T-CONCESSION-001` : création concession valide ;
- `T-CONCESSION-002` : validation saisie (nom manquant) ;
- `T-RECHERCHE-001` : résultats filtrés.

Implémentation :
```typescript
describe('T-CONCESSION-001', () => {
  it('should create a valid concession', () => { ... });
});
```

## Conventions d'implémentation des tests

### Tests unitaires

#### Syntaxe Vitest

```typescript
import { describe, it, expect, beforeEach, afterEach } from 'vitest';

describe('T-SCHEMA-001: Entité Concession', () => {
  let db: Database;

  beforeEach(async () => {
    db = await initTestDatabase();
  });

  afterEach(async () => {
    await db.close();
  });

  it('should validate concession with required fields', () => {
    const concession = {
      numero: 'C001',
      proprietaire: 'Dupont',
      date_acquisition: '2020-01-15',
    };
    expect(validateConcession(concession)).toBe(true);
  });

  it('should reject concession with missing proprietaire', () => {
    const invalid = { numero: 'C002', date_acquisition: '2020-01-15' };
    expect(validateConcession(invalid)).toBe(false);
  });
});
```

#### Assertions attendues

- Validités positives (happy path) ;
- Cas limites (null, empty, min/max) ;
- Cas d'erreur (validation, contraintes) ;
- Comportement en absence de données.

#### Taux de couverture minimale

- **Métier critique** : ≥ 85 % des branches ;
- **Métier secondaire** : ≥ 75 % ;
- **Infrastructure** : pas d'exigence formelle (mais > 0).

### Tests d'intégration

#### Structure avec fixtures

```typescript
describe('T-CONCESSION-003: Créer concession en base', () => {
  let db: Database;

  beforeEach(async () => {
    db = await initTestDatabase('tests/fixtures/init_mvp.sql');
  });

  it('should persist concession and return ID', async () => {
    const cmd = new CreateConcessionCommand({
      numero: 'C-TEST-001',
      proprietaire: 'Test Owner',
      date_acquisition: '2026-01-01',
    });

    const result = await invokeCommand(cmd);
    
    expect(result.id).toBeDefined();
    expect(result.success).toBe(true);
    
    const persisted = await db.query('SELECT * FROM concessions WHERE id = ?', [result.id]);
    expect(persisted[0].proprietaire).toBe('Test Owner');
  });

  afterEach(async () => {
    await db.close();
  });
});
```

#### Nettoyage des données

- Chaque test d'intégration démarre avec `init_mvp.sql` frais ;
- Les modifications restent isolées au test (pas de pollution inter-tests) ;
- Les fixtures sont versionées et reproductibles sur tout OS.

### Tests E2E (Playwright)

#### Structure Playwright

```typescript
import { test, expect } from '@playwright/test';

test.describe('T-CONCESSION-004: Créer concession via interface', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:5173'); // Tauri app
    await page.reload(); // Assurer base test
  });

  test('should create and display new concession', async ({ page }) => {
    // Navigation
    await page.click('text=Nouvelles concessions');
    
    // Formulaire
    await page.fill('input[name="numero"]', 'C-E2E-001');
    await page.fill('input[name="proprietaire"]', 'Test User');
    await page.click('button:has-text("Valider")');
    
    // Assertions
    await expect(page.locator('text=C-E2E-001')).toBeVisible();
    await expect(page.locator('text=Test User')).toBeVisible();
  });

  test('should display validation error on missing field', async ({ page }) => {
    await page.click('text=Nouvelles concessions');
    await page.fill('input[name="numero"]', 'C-E2E-002');
    await page.click('button:has-text("Valider")');
    
    await expect(page.locator('text=Propriétaire requis')).toBeVisible();
  });
});
```

#### Assertions visuelles

- Vérifier présence/absence d'éléments ;
- Valider valeurs affichées (texte, attributs) ;
- Tester interactions (clic, saisie, navigation) ;
- Capturer écrans en cas d'anomalie.

#### Timeouts et attentes

```typescript
// Attendre chargement avant assertion
await expect(page.locator('table')).toHaveCount(1, { timeout: 5000 });
await page.waitForLoadState('networkidle');
```

## Conventions de données de test

### Fixture init_mvp.sql

Données standardisées reproduites pour chaque test :

```sql
-- Cimetière
INSERT INTO cimeteries (id, name, municipality, created_at) VALUES
  (1, 'Cimetière Municipal', 'Test City', '2026-01-01');

-- Sections
INSERT INTO sections (id, cemetery_id, name, capacity, status) VALUES
  (1, 1, 'Section A', 100, 'active'),
  (2, 1, 'Section B', 100, 'active'),
  (3, 1, 'Section C', 50, 'active');

-- Emplacements
INSERT INTO emplacements (id, section_id, numero, statut, proprietaire_id) VALUES
  (1, 1, 'A001', 'free', NULL),
  (2, 1, 'A002', 'occupied', 10),
  (3, 2, 'B001', 'reserved', NULL),
  -- ... autres
  ;

-- Concessions
INSERT INTO concessions (id, numero, proprietaire, date_acquisition, date_expiration, statut) VALUES
  (1, 'C001', 'Dupont', '2020-01-15', '2030-01-15', 'active'),
  -- ... autres
  ;

-- Défunts
INSERT INTO defunts (id, nom, prenom, date_deces, concession_id) VALUES
  (1, 'Dupont', 'Jean', '2020-02-01', 1),
  -- ... autres
  ;
```

### Dénomination des données de test

Utiliser un préfixe identifiable : `TEST`, `E2E`, `FIXTURE` :
- Concession : `C-TEST-001`, `C-E2E-002` ;
- Personne : `TEST-Dupont`, `E2E-Martin` ;
- Section : `Section Test`, `Plan E2E` ;
- Emplacement : `TEST-001`, `E2E-A01`.

Permet d'isoler les résultats de test et d'éviter collision avec données réelles.

## Gestion des résultats et rapports

### Format de rapport de test

Après exécution de chaque suite (unitaire, intégration, E2E) :

```markdown
# Résultats Tests [Domaine] - [Date] [Heure]

## Résumé exécutif
- **Durée totale** : X min Y sec
- **Nombre de tests** : N
- **Réussis** : M (X.X%)
- **Échoués** : K
- **Ignorés** : L

## Détail des échecs

| Test ID | Nom | Erreur | Stack trace |
| --- | --- | --- | --- |
| T-CONCESSION-001 | ... | ... | ... |

## Mesures de couverture (unitaire uniquement)
- Statements : X%
- Branches : Y%
- Functions : Z%

## Observations
- [Anomalies détectées ou comportements inattendus]

## Prochaines étapes
- [Actions recommandées]
```

### Trace de régression entre phases

Avant chaque phase, exécuter l'ensemble des tests des phases précédentes pour vérifier absence de régression :
- Phase 2 : relancer Phase 1 + Phase 2 ;
- Phase 3 : relancer Phases 1-2 + Phase 3 ;
- etc.

Tout échec de régression est **bloquant**.

## Critères d'acceptation des tests

### Avant livraison

Un test livré doit satisfaire :

1. **Code** : passant localement sur Windows et Linux ;
2. **Documentation** : identifiant T-XXX-YYY, description du cas testé ;
3. **Couverture** : domaine et cas limites traités ;
4. **Isolation** : aucune dépendance d'ordre d'exécution ;
5. **Reproductibilité** : résultat identique sur 3 exécutions consécutives ;
6. **Performance** : unitaire < 5s, intégration < 30s, E2E < 5 min total.

### Anomalies dans les tests

Si un test échoue sans cause métier identifiée (problème infrastructure, timing, flakiness) :
1. Ajouter une marque `@flaky` temporaire ;
2. Investiguer la cause (timing, état précédent, environnement) ;
3. Corriger ou documenter la contournement ;
4. Vérifier stabilité sur 10 exécutions avant enlever `@flaky`.

## Intégration continue

### GitHub Actions

Chaque commit doit déclencher :

```yaml
- Unitaires : `npm run test:unit` (Vitest)
- Intégration : `npm run test:integration`
- E2E : `npm run test:e2e:chromium` (Windows) + `:linux` (Linux)
- Couverture : rapport de couverture uploadé en artefact
- Blocage : tout échec bloque le merge en main
```

### Format des commit messages pour tests

```
test(qa): T-CONCESSION-001 create concession validator

- Add unit test for concession creation
- Cover validation of required fields (numero, proprietaire)
- Test edge cases (accented characters, very long names)
- Coverage: 92% of validator functions
```

## Communication et escalade

### Anomalies bloquantes

Anomalie bloquante : tout flux critique échoué ou régression détectée.

```markdown
## 🚫 Anomalie bloquante [ID]
- **Test** : T-CONCESSION-001
- **Phase** : MVP-03
- **Symptôme** : création concession échoue en base
- **Reproductibilité** : 100% sur fixtures
- **Impact** : flux critique entravé
- **Assigné à** : backend (MVP-04)
```

### Anomalies non-bloquantes

Anomalies UI mineures, timing, flakiness non-reproductible :

```markdown
## ⚠️ Anomalie mineure [ID]
- **Test** : T-EMPLACEMENT-003 (flaky)
- **Fréquence** : 1/10 exécutions
- **Cause supposée** : timing réseau
- **Contournement** : ajouter délai d'attente
- **Impact** : CI bloque parfois à tort, à investiguer
```

## Checklist de validation par phase

### Phase 1 (Noyau métier)
- [ ] Tests unitaires schéma et migrations passent ;
- [ ] Couverture métier ≥ 80 % ;
- [ ] Aucune fuite mémoire en test intégration ;
- [ ] Rapport de couverture généré et reviewed ;
- [ ] Aucune régression Phase 1 détectée.

### Phase 2 (Interface métier)
- [ ] Tests unitaires composants React passent ;
- [ ] Tests E2E dashboard, listes, fiches exécutés ;
- [ ] Capture d'écrans comparées pour déviations UI ;
- [ ] Temps de chargement < seuils ;
- [ ] Aucune régression Phases 1-2 détectée.

### Phase 3 (Cartographie)
- [ ] Tests E2E cartographie (zoom/pan, sélection) passent ;
- [ ] Rendu identique Windows/Linux ;
- [ ] Cohérence sélection emplacement ↔ données ;
- [ ] Aucune régression Phases 1-3 détectée.

### Phase 4 (Documents, alertes, sauvegarde)
- [ ] Tests E2E alertes déclenchées/affichées ;
- [ ] PDF généré valide (format, contenu) ;
- [ ] Sauvegarde/restauration intégrité vérifiée ;
- [ ] Aucune régression Phases 1-4 détectée.

### Phase 5 (Packaging et audit final)
- [ ] Installation Windows et Linux réussies ;
- [ ] Tests E2E exécutés sur app installée ;
- [ ] Validation manuelle checklist complète ;
- [ ] Rapport QA final avec risques résiduels ;
- [ ] Aucune régression détectée.

## Ressources et références

- **Vitest docs** : https://vitest.dev/ ;
- **Playwright docs** : https://playwright.dev/ ;
- **React Testing Library** : https://testing-library.com/react ;
- **SPEC.md** : spécifications métier ;
- **ROADMAP.md** : phases et dépendances ;
- **agents/STATUS.md** : suivi global du projet.
