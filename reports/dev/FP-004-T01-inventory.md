# FP-004-T01 — Inventaire des usages de `plots` et contrats à préserver

**Date** : 2026-08-20  
**Status** : Livrable pour FP-004  
**Responsable** : Claude Code (Agent FP004-T01)  

---

## Résumé

Ce rapport trace l'inventaire complet des usages actuels de la table `plots` et des contrats relationnels à préserver lors de la transition FP-004 vers une hiérarchie normalisée (sections → carrés → rangées → emplacements).

L'analyse couvre :
- Schéma SQL et migrations
- Modèles Rust (core models et DTOs)
- Repository et accès données
- Commandes Tauri exposées
- Bindings TypeScript générés
- Consommateurs côté frontend (hooks, pages, composants)
- Tests intégration et E2E
- Points de compatibilité critiques à maintenir

---

## 1. Définition de la table `plots` — État actuel

### 1.1 Schéma SQL

**Fichier** : `src-tauri/migrations/001_initial_schema.sql` (lignes 13–25)

```sql
CREATE TABLE IF NOT EXISTS plots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cemetery_id INTEGER NOT NULL REFERENCES cemeteries(id),
    section TEXT,
    row INTEGER,
    number INTEGER,
    capacity INTEGER DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'available',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_plots_cemetery_id ON plots(cemetery_id);
```

**Colonnes définies** :
- `id` : Identifiant unique (clé primaire auto-incrémentée)
- `cemetery_id` : Référence étrangère vers `cemeteries(id)` — **CONTRAT CRITIQUE**
- `section` : Code section (TEXT nullable, ex. "A", "B1", "NORD")
- `row` : Numéro rangée (INTEGER nullable, ex. 1, 2, 3)
- `number` : Numéro emplacement (INTEGER nullable, ex. 1, 5, 12)
- `capacity` : Capacité totale (INTEGER, défaut 1) — **CONTRAT CRITIQUE**
- `status` : État de l'emplacement (TEXT, défaut 'available') — **CONTRAT CRITIQUE**
- `created_at` : Horodatage création (TEXT ISO 8601 UTC)
- `updated_at` : Horodatage modification (TEXT ISO 8601 UTC)

**Index** :
- `idx_plots_cemetery_id` : Index sur `cemetery_id` pour les requêtes par cimetière

**Contrainte de clé étrangère** :
- `cemetery_id` REFERENCES `cemeteries(id)` (avec PRAGMA foreign_keys = ON)

---

### 1.2 Relations avec autres tables

**Relation 1 : `plots` ← `cemeteries` (many-to-one)**
- Un emplacement appartient à un et un seul cimetière
- Requête fréquente : `SELECT * FROM plots WHERE cemetery_id = ?`
- **À préserver absolument** : la colonne `cemetery_id`

**Relation 2 : `plots` → `concessions` (one-to-many, optional)**
- Une concession peut référencer une ou zéro emplacement
- **Fichier** : `src-tauri/migrations/001_initial_schema.sql` (lignes 27–37)
  ```sql
  CREATE TABLE IF NOT EXISTS concessions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      cemetery_id INTEGER NOT NULL REFERENCES cemeteries(id),
      plot_id INTEGER REFERENCES plots(id),  -- ← RÉFÉRENCE À PLOTS
      ...
  );
  CREATE INDEX IF NOT EXISTS idx_concessions_plot_id ON concessions(plot_id);
  ```
- **À préserver** : la colonne `plot_id` dans `concessions` et son intégrité référentielle

---

## 2. Modèles Rust — Domain et DTOs

### 2.1 Core Model : `Plot`

**Fichier** : `src-tauri/src/core/models/plot.rs`

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Plot {
    pub id: i64,
    pub cemetery_id: i64,
    pub section: Option<String>,
    pub row: Option<i32>,
    pub number: Option<i32>,
    pub capacity: i32,
    pub status: String,
    pub created_at: String,
    pub updated_at: String,
}

impl Plot {
    pub fn new(
        cemetery_id: i64,
        section: Option<String>,
        row: Option<i32>,
        number: Option<i32>,
        capacity: i32,
    ) -> Self { ... }
}
```

**Champs** : Miroir exact du schéma SQL  
**Sérialization** : serde (JSON pour Tauri commands)  
**Utilisation** : Entité métier interne au backend Rust

**Contrats à préserver** :
- Constructeur `Plot::new()` signature
- Types des champs (i64, i32, String, Option)
- Champs `section`, `row`, `number`, `capacity`, `status`

### 2.2 DTO : `PlotDTO`, `CreatePlotRequest`, `UpdatePlotRequest`

**Fichier** : `src-tauri/src/dto/plot.rs`

```rust
#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct PlotDTO {
    pub id: i64,
    pub cemetery_id: i64,
    pub section: Option<String>,
    pub row: Option<i32>,
    pub number: Option<i32>,
    pub capacity: i32,
    pub status: String,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct CreatePlotRequest {
    pub cemetery_id: i64,
    pub section: Option<String>,
    pub row: Option<i32>,
    pub number: Option<i32>,
    pub capacity: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct UpdatePlotRequest {
    pub section: Option<String>,
    pub row: Option<i32>,
    pub number: Option<i32>,
    pub capacity: Option<i32>,
    pub status: Option<String>,
}
```

**Dérivé avec** : specta::Type pour génération TypeScript (post-MVP via tauri-specta)

**Contrats à préserver** :
- `PlotDTO` : structure JSON sérialisée par les Tauri commands
- `CreatePlotRequest` : signature pour création
- `UpdatePlotRequest` : signature pour mise à jour (tous champs optionnels)
- `status` type : String (pas d'enum Rust actuellement, mais enum TypeScript)

---

## 3. Repository — Accès aux données

**Fichier** : `src-tauri/src/db/repositories/plot_repo.rs`

### 3.1 Opérations CRUD exposées

```rust
pub struct PlotRepository;

impl PlotRepository {
    pub fn list(conn: &Connection, cemetery_id: i64) -> AppResult<Vec<PlotDTO>>
    pub fn get(conn: &Connection, id: i64) -> AppResult<PlotDTO>
    pub fn create(conn: &Connection, plot: &Plot) -> AppResult<PlotDTO>
    pub fn update(conn: &Connection, id: i64, plot: &Plot) -> AppResult<PlotDTO>
}
```

**Détails** :

1. **list(cemetery_id)** — Liste tous les emplacements d'un cimetière
   - Requête : `SELECT ... FROM plots WHERE cemetery_id = ? ORDER BY section, row, number`
   - **Tri critique** : section → row → number (hiérarchique)
   - Retour : `Vec<PlotDTO>` ordonnée
   - **Consommateur clé** : CemeteryMap, pages concessions

2. **get(id)** — Récupère un emplacement par id
   - Requête : `SELECT ... FROM plots WHERE id = ?`
   - Erreur : `AppError::NotFound` si absent
   - **Consommateur clé** : détails concession, map

3. **create(plot)** — Crée un nouvel emplacement
   - INSERT avec tous les champs
   - Retour : PlotDTO avec id généré
   - **Validation** : cemetery_id référence valide (FK)

4. **update(id, plot)** — Met à jour un emplacement
   - Vérifie existence avant UPDATE
   - **Champs modifiables** : section, row, number, capacity, status, cemetery_id
   - Retour : PlotDTO mis à jour

### 3.2 Tests du repository

**Fichier** : `src-tauri/src/db/repositories/plot_repo.rs` (lignes 105–342)

Tests couverts :
- `test_create_and_get_plot()` — Création + récupération
- `test_list_plots()` — Tri par section/row/number
- `test_update_plot()` — Modification status
- `test_get_non_existent_plot()` — Gestion erreur
- `test_update_non_existent_plot()` — Gestion erreur

**Contrats à préserver** :
- Signature des 4 méthodes
- Ordre de tri (section ASC, row ASC, number ASC)
- Gestion des erreurs (NotFound vs Database)

---

## 4. Commandes Tauri

**Fichier** : `src-tauri/src/commands/plot.rs`

### 4.1 Commandes exposées vers TypeScript

```rust
#[tauri::command]
pub fn list_plots(state: State<DbConnection>, cemetery_id: i64) -> Result<Vec<PlotDTO>, String>

#[tauri::command]
pub fn get_plot(state: State<DbConnection>, id: i64) -> Result<PlotDTO, String>

#[tauri::command]
pub fn create_plot(state: State<DbConnection>, req: CreatePlotRequest) -> Result<PlotDTO, String>

#[tauri::command]
pub fn update_plot(state: State<DbConnection>, id: i64, req: UpdatePlotRequest) -> Result<PlotDTO, String>
```

### 4.2 Sérialisation requêtes/réponses

**Sérialisation requêtes** :
- `create_plot` : paramètre nommé `request` (conforme Tauri)
- `update_plot` : paramètres nommés `id`, `request`
- Décodage JSON automatique par serde

**Sérialisation réponses** :
- Toutes retournent JSON (PlotDTO ou Vec<PlotDTO>)
- Erreurs retournées en `Result<T, String>` (message d'erreur texte)

### 4.3 Enregistrement des commandes

**Fichier** : `src-tauri/src/commands/mod.rs`

```rust
pub mod plot;
pub use plot::*;
```

**Fichier** : `src-tauri/src/main.rs`

Les 4 commandes plot sont automatiquement enregistrées lors du build Tauri.

**Contrats à préserver** :
- Noms de commandes (list_plots, get_plot, create_plot, update_plot)
- Signatures et types de paramètres
- Format JSON des DTOs

---

## 5. Bindings TypeScript

**Fichier** : `src/types/bindings.ts` (lignes 73–103)

```typescript
export interface PlotDTO {
  id: number;
  cemetery_id: number;
  section: string | null;
  row: number | null;
  number: number | null;
  capacity: number;
  status: PlotStatus;
  created_at: string;
  updated_at: string;
}

export type PlotStatus = "available" | "occupied" | "reserved" | "unavailable";

export interface CreatePlotRequest {
  cemetery_id: number;
  section?: string;
  row?: number;
  number?: number;
  capacity: number;
}

export interface UpdatePlotRequest {
  section?: string;
  row?: number;
  number?: number;
  capacity?: number;
  status?: PlotStatus;
}
```

**Source** : "AUTO-MIRRORED FROM src-tauri/src/dto/*.rs" (commentaire ligne 2)  
**Synchronisation** : manuelle (cible : remplacer avec specta post-MVP-06)

### 5.1 Type PlotStatus enum

```typescript
export type PlotStatus = "available" | "occupied" | "reserved" | "unavailable";
```

**États gérés** :
- `"available"` — Emplacement libre
- `"occupied"` — Occupé (concession active)
- `"reserved"` — Réservé (prévu)
- `"unavailable"` — Indisponible (destruction, travaux)

**Limitation actuelle** : pas d'enum côté Rust (STRING SQL), mais TypeScript type union

**Contrats à préserver** :
- Les 4 états PlotStatus (ou au minimum "available", "occupied")
- Interface PlotDTO et requêtes

---

## 6. Couche Tauri — Wrapper d'invocation

**Fichier** : `src/lib/tauri.ts` (lignes 27–31)

```typescript
export const listPlots = (cemeteryId: number) => 
  invoke<PlotDTO[]>("list_plots", { cemeteryId });
export const getPlot = (id: number) => 
  invoke<PlotDTO>("get_plot", { id });
export const createPlot = (req: CreatePlotRequest) => 
  invoke<PlotDTO>("create_plot", { request: req });
export const updatePlot = (id: number, req: UpdatePlotRequest) => 
  invoke<PlotDTO>("update_plot", { id, request: req });
```

**Utilisation** : Appellé par les hooks (cf. section 7)  
**Paramètres** : Noms doivent correspondre exactement aux `#[tauri::command]` côté Rust

**Contrats à préserver** :
- Noms de fonctions (listPlots, getPlot, etc.)
- Noms de paramètres Tauri (cemetery_id, id, request)
- Types retournés (PlotDTO, Vec<PlotDTO>)

---

## 7. Hooks React — Abstraction métier

**Fichier** : `src/hooks/usePlots.ts`

```typescript
export function usePlots(cemeteryId: number | null, options?: UsePlotsOptions) {
  return useQuery<PlotDTO[]>(
    () => listPlots(cemeteryId!),
    { enabled: cemeteryId !== null && options?.enabled !== false }
  );
}

export function usePlot(id: number | null, options?: UsePlotsOptions) {
  return useQuery<PlotDTO>(
    () => getPlot(id!),
    { enabled: id !== null && options?.enabled !== false }
  );
}

export async function createPlotAsync(request: CreatePlotRequest) {
  try {
    return await createPlot(request);
  } catch (error) {
    throw error instanceof Error ? error : new Error(String(error));
  }
}

export async function updatePlotAsync(id: number, request: UpdatePlotRequest) {
  try {
    return await updatePlot(id, request);
  } catch (error) {
    throw error instanceof Error ? error : new Error(String(error));
  }
}
```

**Pattern** : useQuery pour les GETs (avec caching automatique), async pour POST/PUT

**Contrats à préserver** :
- Noms des hooks (usePlots, usePlot)
- Noms des async (createPlotAsync, updatePlotAsync)
- Signature : accept cemetery_id ou id nullable

---

## 8. Composants frontend — Consommateurs

### 8.1 CemeteryMap

**Fichier** : `src/components/map/CemeteryMap.tsx` (lignes 1–100+)

**Dépendances** :
- Import : `PlotMapDTO` (depuis bindings)
- Utilise : `data.plots` (array de plots avec section, row, number, status)
- Rendu : SVG grid par section/row

**Logique** :
```typescript
const groupedPlots = groupPlotsBySection(data.plots);
// Groupe par section, puis par row
// Affiche comme grille 2D colorisée par status
```

**Couleurs de status** :
```typescript
case "available": return "#10b981";  // vert
case "occupied": return "#3b82f6";   // bleu
case "reserved": return "#f59e0b";   // orange
case "unavailable": return "#9ca3af"; // gris
```

**Contrats à préserver** :
- Les 4 status et leurs couleurs
- Structure PlotMapDTO avec section, row, number, status
- Tri naturel section/row/number

### 8.2 PlotViewer

**Fichier** : `src/components/map/PlotViewer.tsx`

**Dépendances** :
- Input : `PlotDTO | null`
- Affiche : section, row, number en SVG mini-card
- Utilisé dans : fiche concession, détails

**Contrats à préserver** :
- Accept PlotDTO | null
- Affichage de section, row, number

### 8.3 Pages consommateurs

**ConcessionsPage.tsx** (lignes 8, 33, 51)
```typescript
const [plots, setPlots] = useState<Map<number, PlotDTO>>(new Map());
// Charge tous les plots pour les afficher en liste/map
```

**ConcessionCreatePage.tsx** (lignes 7, 18)
```typescript
const [plots, setPlots] = useState<PlotDTO[]>([]);
// Dropdown de sélection d'emplacement pour création concession
```

**ConcessionEditPage.tsx** (lignes 7, 18)
```typescript
const [plots, setPlots] = useState<PlotDTO[]>([]);
// Dropdown de sélection/modification d'emplacement
```

**Contrats à préserver** :
- Possible charger plots pour un cimetière (usePlots hook)
- Possible lister et mapper PlotDTO vers UI

---

## 9. Tests — Couverture

### 9.1 Tests d'intégration backend

**Fichier** : `src-tauri/tests/integration_plot.rs`

Tests :
- `test_full_plot_workflow()` — Création cemetery → plot → list → get
- `test_plot_create_and_list()` — Création multiple avec tri

**Exécution** :
```bash
cargo test --test integration_plot
```

### 9.2 Tests frontend

**Fichier** : `src/__tests__/tauri.test.ts` (lignes 21–40)

Imports :
```typescript
import { listPlots, getPlot } from "@/lib/tauri";
import type { PlotDTO } from "@/types/bindings";
```

Mocking : @tauri-apps/api/core mocked

**Fichier** : `src/__tests__/bindings.test.ts`

Teste : Types bindings TypeScript générés/maintenus

### 9.3 Tests E2E

**Fichier** : `tests/e2e/09-cartography-map.spec.ts`
- Test : map rendering, click plot, sélection

**Fichier** : `tests/e2e/03-concessions-list.spec.ts`
- Test : affichage plots dans liste concessions

**Fichier** : `tests/e2e/04-concession-detail.spec.ts`
- Test : affichage plot detail dans fiche concession

**Exécution** :
```bash
npm run test:e2e
```

---

## 10. État des migrations

### 10.1 Migration 001 (initial schema)

**Fichier** : `src-tauri/migrations/001_initial_schema.sql`

Crée table `plots` avec schéma ci-dessus.

### 10.2 Migrations ultérieures

**Fichier** : `src-tauri/src/db/migrations.rs`

Migrations ultérieures (0007-0010) :
- 0006 : Create alerts table (no change to plots)
- 0007 : Extend concessions for lifecycle (no direct change to plots)
- 0008 : Create municipalities table (no change to plots)
- 0009 : Extend cemeteries for municipalities (no change to plots)
- 0010 : Add insee_code and email to municipalities (no change to plots)

**Contrats à préserver** :
- Table `plots` doit rester existante et fonctionnelle
- Colonnes core (id, cemetery_id, section, row, number, capacity, status) non suppressibles

---

## 11. Contrats historiques critiques

### 11.1 Niveau 1 — Impossible à casser

Ces contrats doivent être préservés intégralement pour ne pas briser le MVP en production :

| Contrat | Raison | Impact de casser |
|---------|--------|-----------------|
| `plots.id` PK auto-incr | Clé primaire, tous les records existants | Migration catastrophique, perte de FK |
| `plots.cemetery_id` FK | Relation avec cemeteries | Orphelins, intégrité référentielle brisée |
| `plots.section`, `plots.row`, `plots.number` | Localisation spatiale, UI map | Perte de localisation |
| `plots.capacity` | Métier (limitation places) | Capacité pas tracée |
| `plots.status` enum (available, occupied, reserved, unavailable) | UI colorisée, filtres | Map cassée |
| `concessions.plot_id` FK → plots.id | Lien concession → emplacement | Perte association concession/plot |

### 11.2 Niveau 2 — Breakers de fonctionnalité précis

| Contrat | Utilisation | Risque |
|---------|------------|--------|
| PlotRepository::list(cemetery_id) tri section/row/number | CemeteryMap, ConcessionsPage | Map disorder, UI confuse |
| listPlots, getPlot Tauri commands | All frontend data fetch | Network break |
| PlotDTO TypeScript struct | Frontend state, props | Type mismatch, runtime error |
| PlotStatus "available", "occupied" | Color code, filter | Map broken |

### 11.3 Niveau 3 — Fortement recommandé de garder

| Contrat | Raison | Alternative coûteuse |
|---------|--------|----------------------|
| usePlots, usePlot hooks | DRY, standardization | Réécrire tous les consommateurs |
| createPlotAsync, updatePlotAsync | Error handling, try/catch | Dupliquer logic partout |
| PlotViewer component | Réutilisable display | Redévelopper plusieurs fois |
| CemeteryMap SVG grid logic | Complex layout | Réécrire + retests |

---

## 12. Fichiers consommateurs par rôle

### 12.1 Consommateurs Rust (backend)

```
src-tauri/src/
├── core/models/plot.rs               [CORE MODEL]
├── dto/plot.rs                       [DTO DEFINITIONS]
├── db/repositories/plot_repo.rs      [REPOSITORY + TESTS]
├── commands/plot.rs                  [TAURI COMMANDS]
├── commands/mod.rs                   [EXPORT]
├── db/migrations.rs                  [MIGRATION RUNNER]
└── main.rs                           [COMMAND REGISTRATION]

src-tauri/migrations/
├── 001_initial_schema.sql            [PLOTS TABLE DEF]
└── 0006-0010...                      [ADDITIVE MIGRATIONS]

src-tauri/tests/
├── integration_plot.rs               [TESTS]
└── integration_concession.rs         [FK TESTING]
```

### 12.2 Consommateurs TypeScript (frontend)

```
src/
├── types/bindings.ts                 [INTERFACES MIRROR]
├── lib/tauri.ts                      [COMMAND WRAPPERS]
├── hooks/usePlots.ts                 [DATA FETCHING]
├── components/map/CemeteryMap.tsx    [RENDERING]
├── components/map/PlotViewer.tsx     [DETAIL CARD]
├── pages/ConcessionsPage.tsx         [CONSUMER]
├── pages/ConcessionCreatePage.tsx    [CONSUMER]
├── pages/ConcessionEditPage.tsx      [CONSUMER]
└── __tests__/                        [TESTS]
    ├── tauri.test.ts
    └── bindings.test.ts

tests/e2e/
├── 09-cartography-map.spec.ts
├── 03-concessions-list.spec.ts
└── 04-concession-detail.spec.ts
```

---

## 13. Points de compatibilité — Résumé pour FP-004

### 13.1 À préserver strictement pendant la migration

1. **Schéma SQL**
   - Colonne `plots.id` — clé primaire (sera réutilisée ou mappée)
   - Colonne `plots.cemetery_id` — FK (conservation obligatoire)
   - Colonne `plots.status` — enum 4 états (minimum)
   - Foreign key `concessions.plot_id → plots.id`

2. **Modèles Rust**
   - Plot::new() constructor
   - PlotDTO sérialisable en JSON
   - UpdatePlotRequest optionality

3. **Repository interface**
   - list(cemetery_id) → sorted Vec<PlotDTO>
   - get(id) → PlotDTO ou NotFound
   - create, update signatures

4. **Tauri commands**
   - list_plots, get_plot, create_plot, update_plot
   - Paramètres et types échanges

5. **TypeScript bindings**
   - PlotDTO interface
   - PlotStatus union type (au minimum "available", "occupied")
   - CreatePlotRequest, UpdatePlotRequest

6. **Frontend hooks**
   - usePlots(cemeteryId)
   - usePlot(id)
   - createPlotAsync, updatePlotAsync

---

## 14. Validation et tests à exécuter

### 14.1 Tests à passer avant/après

```bash
# Backend
cargo test --test integration_plot

# Frontend
npm test -- src/__tests__/tauri.test.ts
npm test -- src/__tests__/bindings.test.ts

# E2E
npm run test:e2e -- 09-cartography-map
npm run test:e2e -- 03-concessions-list
npm run test:e2e -- 04-concession-detail
```

### 14.2 Validation de contrats

```bash
# Vérifier existence et intégrité tables
sqlite3 data.db "SELECT sql FROM sqlite_master WHERE type='table' AND name='plots';"

# Vérifier FK
sqlite3 data.db "PRAGMA foreign_key_list(concessions);" # plot_id

# Vérifier bindings TypeScript générés (post-specta)
rg "PlotDTO|PlotStatus|CreatePlotRequest|UpdatePlotRequest" src/types/bindings.ts
```

---

## 15. Conclusion

L'inventaire ci-dessus documente l'état complet de l'utilisation actuelle de `plots`. Les **contrats niveau 1** (schéma core, relations FK, commands Tauri, bindings TS) doivent être préservés ou explicitement mappés pendant FP-004 pour garantir la non-régression des fonctionnalités MVP en place.

Les tâches FP004-T02 à FP004-T06 peuvent dès lors procéder à la conception de la hiérarchie normalisée (sections → carrés → rangées → emplacements) en sachant exactement quels contrats doivent rester stables pour la transition.

---

**Généré par** : FP004-T01 Inventory Trace  
**Date signature** : 2026-08-20 12:17 GMT+2  
**Livrables** : Ce rapport seul (no code changes, documentation only)
