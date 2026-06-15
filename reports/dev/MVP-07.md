# MVP-07 — Définir le format cartographique MVP

**Date :** 2026-06-15  
**Agent :** mapping  
**Statut :** ✅ Stabilisé  
**Dépend de :** MVP-04 ✅ Terminé

## Objectif

Concevoir le format minimal de représentation cartographique d'un cimetière et de ses emplacements, sans implémenter le rendu visuel (MVP-14), en définissant :
1. Les structures de données cartographiques ;
2. La relation entre cimetière, secteur, rangée, emplacement et coordonnées ;
3. Le format d'échange cartographie ↔ base de données ;
4. Les contraintes de rendu pour MVP-14 ;
5. Les critères d'acceptation pour débloquer le mapping.

## Tâches clés

- [x] Analyser le schéma plots stabilisé (MVP-04)
- [x] Définir le système de coordonnées cartographiques
- [x] Spécifier la structure de données de plan
- [x] Documenter les relations métier avec secteur/rangée/emplacement
- [x] Prévoir les contraintes de rendu et transformation
- [x] Établir les critères de validation pour MVP-14

## 1. Architecture cartographique MVP

### 1.1 Modèle de données existant (plots table, MVP-04)

La table `plots` (emplacements) contient déjà les données essentielles :

```sql
CREATE TABLE plots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cemetery_id INTEGER NOT NULL,
    section TEXT,           -- "A", "B", etc.
    row INTEGER,            -- 1, 2, 3, ...
    number INTEGER,         -- 1, 2, 3, ... (position dans la rangée)
    capacity INTEGER DEFAULT 1,
    status TEXT DEFAULT 'available',  -- available, occupied, reserved
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (cemetery_id) REFERENCES cemeteries(id)
);
```

**Observations clés :**
- Les identifiants spatiaux (section, row, number) permettent déjà une localisation logique
- Aucune coordonnée géométrique (x, y, polygone) n'est stockée en base MVP
- Le statut (available, occupied, reserved) peut être enrichi ultérieurement

### 1.2 Hiérarchie cartographique MVP

Structure logique d'un cimetière :

```
Cemetery (cimetière)
    └── Section (secteur, ex. "A")
        └── Row (rangée, ex. 1, 2, 3)
            └── Plot (emplacement, ex. 1, 2, 3)
                ├── id (identifiant unique)
                ├── status (disponibilité)
                ├── capacity (capacité)
                └── [future] coordonnées géométriques
```

**Exemple de localisation logique :**
- Cimetière : "Cimetière municipal de Montfort"
- Secteur : "A"
- Rangée : "3"
- Emplacement : "5"
→ Chemin cartographique : `A/3/5` ou identifiant unique `plots.id = 42`

### 1.3 Système de coordonnées — MVP (approche simple)

**Choix pour MVP :** Coordonnées logiques (section, row, number) + placeholder pour géométrie future.

Pour MVP-07 et MVP-14, **pas de stockage géométrique en base**, mais :
- Les emplacements sont positionnés par défaut sur une **grille régulière virtuelle**
- Chaque plot occupe une cellule (1 unité × 1 unité)
- Les rangées et sections s'alignent en grille orthogonale

**Transformation logique → visuelle (pour MVP-14) :**

```
Coordonnées logiques:  section="A", row=1, number=3
            ↓
Grille virtuelle:      x = (section_index * section_width) + (number - 1) * plot_width
                       y = (row - 1) * plot_height
            ↓
Rendu visuel:          Rectangle ou SVG à (x, y) avec dimensions (plot_width, plot_height)
```

**Paramètres de grille pour MVP-14 :**
- `plot_width` = 50 pixels (pour affichage par défaut)
- `plot_height` = 50 pixels
- `section_width` = 10 (nombre max d'emplacements par rangée, ou largeur section)
- `row_height` = 50 pixels

→ **Aucun de ces paramètres n'est stocké en base pour MVP-07**. Ils seront codés en dur dans le composant de rendu MVP-14 et deviendront paramétrables pour MVP-14+.

---

## 2. Structures de données cartographiques MVP

### 2.1 DTOs cartographiques (à ajouter en src-tauri/src/dto/)

Pour l'échange cartographie ↔ frontend, définir les DTOs suivants :

#### PlotMapDTO (vue cartographique d'un plot)

```rust
#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct PlotMapDTO {
    pub id: i64,
    pub cemetery_id: i64,
    pub section: Option<String>,
    pub row: Option<i64>,
    pub number: Option<i64>,
    pub status: String,  // available, occupied, reserved, unavailable
    pub capacity: i64,
    pub occupied_count: i64,  // nombre de défunts inhumés
    pub concession_count: i64, // nombre de concessions
    // Future: geometric coordinates
    // pub x: Option<f64>,
    // pub y: Option<f64>,
    // pub polygon: Option<String>, // GeoJSON si besoin futur
}
```

#### CemeteryMapDTO (vue cartographique d'un cimetière)

```rust
#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct CemeteryMapDTO {
    pub id: i64,
    pub name: String,
    pub commune: Option<String>,
    pub plots: Vec<PlotMapDTO>,
    // Métadonnées de rendu
    pub section_count: i64,     // nombre de secteurs uniques
    pub max_row: i64,           // max rangée observable
    pub max_number: i64,        // max emplacement par rangée
    pub total_capacity: i64,    // capacité totale
    pub occupied_count: i64,    // occupés
    pub available_count: i64,   // disponibles
    // Future: custom geometry bounds
    // pub bounds: Option<GeometryBounds>,
}
```

#### PlotLocationRequest (requête pour chercher un plot)

```rust
#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct PlotLocationRequest {
    pub cemetery_id: i64,
    pub section: Option<String>,
    pub row: Option<i64>,
    pub number: Option<i64>,
}
```

#### PlotStatsSummaryDTO (statistiques pour le rendu)

```rust
#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct PlotStatsSummaryDTO {
    pub total_plots: i64,
    pub available: i64,
    pub occupied: i64,
    pub reserved: i64,
    pub unavailable: i64,
}
```

### 2.2 Fichiers à créer

- `src-tauri/src/dto/plot_map.rs` — PlotMapDTO, CemeteryMapDTO
- `src-tauri/src/dto/plot_location.rs` — PlotLocationRequest
- `src-tauri/src/dto/plot_stats.rs` — PlotStatsSummaryDTO
- `src-tauri/src/dto/mod.rs` — exports

Pas de modification du schéma `plots` existant pour MVP-07.

---

## 3. Relation entre cimetière, secteur, rangée, emplacement et coordonnées

### 3.1 Schéma conceptuel

```
┌─────────────────────────────────────────────────────┐
│ Cemetery (id=1, name="Montfort")                    │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────────┐    ┌──────────────────┐      │
│  │ Section A        │    │ Section B        │      │
│  ├──────────────────┤    ├──────────────────┤      │
│  │ Row 1: [1][2]... │    │ Row 1: [1][2]... │      │
│  │ Row 2: [1][2]... │    │ Row 2: [1][2]... │      │
│  │ Row 3: [1][2]... │    │ Row 3: [1][2]... │      │
│  └──────────────────┘    └──────────────────┘      │
│                                                     │
└─────────────────────────────────────────────────────┘

Chaque [x] = 1 plot avec status (green=available, blue=occupied, etc.)
```

### 3.2 Navigation et localisation

**Chemin logique complet d'un emplacement :**

```
Cimetière ID → Section (string) → Rangée (int) → Emplacement (int) → PlotMapDTO

Exemple requête:
GET /api/cemetery/1/map → CemeteryMapDTO avec tous les plots
GET /api/cemetery/1/section/A/row/3 → PlotMapDTO pour rangée 3 du secteur A
GET /api/plot/42 → PlotMapDTO avec id=42
SEARCH /api/cemetery/1/locate?section=A&row=3&number=5 → PlotMapDTO unique
```

**Stockage en base (MVP-04, inchangé) :**

```
plots.id = 42
plots.cemetery_id = 1
plots.section = "A"
plots.row = 3
plots.number = 5
plots.status = "occupied"
plots.capacity = 1
```

### 3.3 Enrichissement des données cartographiques

Pour enrichir CemeteryMapDTO avant envoi au frontend, le backend MVP doit calculer :

```
1. Pour chaque plot:
   - statut (occupied/available/reserved)
   - nombre de concessions actives
   - nombre de défunts inhumés (via burials)
   
2. Pour le cimetière:
   - listes regroupées par section
   - statistiques d'occupation par section
   - totaux (capacity, occupied, available)
```

**Requête cartographique (MVP-10 ou MVP-11, implémentation future) :**

```rust
pub async fn get_cemetery_map(
    cemetery_id: i64,
) -> Result<CemeteryMapDTO, AppError> {
    // 1. Récupérer tous les plots du cimetière
    let plots = db::get_plots_by_cemetery(cemetery_id)?;
    
    // 2. Pour chaque plot, enrichir avec stats:
    //    - nombre de concessions
    //    - nombre de défunts (via burials)
    //    - recalculer status si nécessaire
    let enriched_plots = plots
        .iter()
        .map(|plot| {
            let occupied_count = db::count_burials_by_plot(plot.id)?;
            let concession_count = db::count_concessions_by_plot(plot.id)?;
            
            PlotMapDTO {
                id: plot.id,
                cemetery_id: plot.cemetery_id,
                section: plot.section.clone(),
                row: plot.row,
                number: plot.number,
                status: plot.status.clone(),
                capacity: plot.capacity,
                occupied_count,
                concession_count,
            }
        })
        .collect();
    
    // 3. Calculer les statistiques de cimetière
    let stats = calculate_cemetery_stats(&enriched_plots);
    
    Ok(CemeteryMapDTO {
        id: cemetery_id,
        name: cemetery.name,
        plots: enriched_plots,
        section_count: count_unique_sections(&enriched_plots),
        max_row: max_row_number(&enriched_plots),
        max_number: max_plot_per_row(&enriched_plots),
        total_capacity: stats.total_capacity,
        occupied_count: stats.occupied,
        available_count: stats.available,
    })
}
```

---

## 4. Format minimal pour afficher un plan simple (MVP-14)

### 4.1 Données en sortie du backend (MVP-07, DTOs)

Le backend MVP-07 fournit uniquement des DTOs et contrats API.  
Le rendu (MVP-14) consomme :

```typescript
// Du côté frontend (MVP-14), data reçue du backend:
interface PlotMapData {
  id: number;
  section: string | null;
  row: number | null;
  number: number | null;
  status: "available" | "occupied" | "reserved" | "unavailable";
  capacity: number;
  occupied_count: number;
  concession_count: number;
}

interface CemeteryMapData {
  id: number;
  name: string;
  plots: PlotMapData[];
  section_count: number;
  max_row: number;
  max_number: number;
  total_capacity: number;
  occupied_count: number;
  available_count: number;
}
```

### 4.2 Transformation logique → géométrie (MVP-14, non-implémenté ici)

Le composant de rendu MVP-14 devra :

1. **Parser les coordonnées logiques** (section, row, number) depuis les plots
2. **Calculer les positions pixels** via la grille virtuelle :
   ```
   section_idx = alphabetic_to_index(section)  // "A"→0, "B"→1, etc.
   x = section_idx * SECTION_WIDTH + (number-1) * PLOT_WIDTH
   y = (row-1) * PLOT_HEIGHT
   ```
3. **Mapper les statuts aux couleurs** :
   - `available` → vert clair (#10b981)
   - `occupied` → bleu (#3b82f6)
   - `reserved` → orange (#f59e0b)
   - `unavailable` → gris (#9ca3af)
4. **Afficher les formes** :
   - Rectangles SVG simples de (PLOT_WIDTH × PLOT_HEIGHT)
   - Ou grille HTML/CSS
   - Ou Canvas 2D
5. **Ajouter les interactions** :
   - Survol → tooltip avec section/row/number
   - Clic → ouvre fiche emplacement
   - Zoom/pan (optionnel pour MVP)

### 4.3 Moteur de rendu recommandé (MVP-14)

Pour MVP-14, **SVG simple sans librairie cartographique** :

```typescript
// Pseudo-code rendu MVP-14 (à implémenter dans MVP-14)
function renderCemeteryMap(cemeteryData: CemeteryMapData) {
  const plots = cemeteryData.plots;
  const grid = buildVirtualGrid(plots);  // group by section/row
  
  return (
    <svg width={grid.width} height={grid.height}>
      {plots.map(plot => (
        <rect
          x={calculateX(plot.section, plot.number)}
          y={calculateY(plot.row)}
          width={PLOT_WIDTH}
          height={PLOT_HEIGHT}
          fill={getColorByStatus(plot.status)}
          stroke="black"
          strokeWidth="1"
          onMouseEnter={() => showTooltip(plot)}
          onClick={() => selectPlot(plot)}
        />
      ))}
    </svg>
  );
}
```

**Pas de Leaflet, MapLibre ou autres lib SIG pour MVP.**  
Décision justifiée : MVP doit rester léger, les données ne sont pas géolocalisées réelles, et une simple grille suffit.

---

## 5. Contraintes de rendu pour MVP-14

### 5.1 Hypothèses de performance

- ✅ Un cimetière MVP aura au maximum 500 emplacements (estimation communale)
- ✅ Rendu SVG sans optimisation → acceptable pour <1000 formes
- ✅ Pas de virtualisation (lazy loading) requise pour MVP
- ✅ Pas de 3D, animation ou WebGL

### 5.2 Format des données stable

**Les DTOs définies en MVP-07 ne doivent pas changer pour MVP-14.**  
MVP-14 doit consommer les DTOs tels que définis, sans modifier leur structure.

Extension future possible (pour MVP-14+) :
- Ajout de `x`, `y`, `polygon` en JSON dans PlotMapDTO
- Ajout de `geometry_bounds` dans CemeteryMapDTO
- Mais ces champs resteraient optionnels et defaults.

### 5.3 Contraintes d'affichage

| Contrainte | Valeur | Raison |
|-----------|--------|--------|
| Taille max plot | 100×100 px | Lisibilité écran |
| Espacement min | 2 px | Distinction visuelle |
| Nombre max sections | 10 (A–J) | Limiter largeur plan |
| Nombre max rangées | 20 | Limiter hauteur plan |
| Nombre max emplacements/rangée | 25 | Limiter dimension cellule |
| Zoom min | 50% | Pour petits écrans |
| Zoom max | 200% | Suffisant pour détails |

### 5.4 Interaction utilisateur (MVP-14)

- ✅ Clic sur emplacement → ouvre fiche détail
- ✅ Survol → affiche coordonnées (section/row/number) + statut
- ✅ Double-clic → édition rapide du statut (optionnel MVP-14+)
- ✅ Filtre visuel par statut (optionnel MVP-14+)
- ⛔ Pan/zoom : optionnel ; si implémenté, via contrôles simples (+ / −)
- ⛔ Pas de dessin/annotation pour MVP

---

## 6. Critères d'acceptation pour débloquer mapping

### 6.1 MVP-07 — Format cartographique (cette tâche)

- [x] DTOs cartographiques définis (`PlotMapDTO`, `CemeteryMapDTO`, etc.)
- [x] Relation entre cimetière/secteur/rangée/emplacement documentée
- [x] Système de coordonnées logiques (section, row, number) validé
- [x] Format d'échange backend/frontend stabilisé
- [x] Contraintes de rendu pour MVP-14 documentées
- [x] Pas de modification du schéma base de données
- [x] Rapport MVP-07.md produit
- [x] `agents/STATUS.md` mis à jour

**Livrable :** `reports/dev/MVP-07.md` (ce document)

### 6.2 Déverrouillage de MVP-14 (rendu cartographique)

**Conditions pour lancer MVP-14 :**

1. ✅ MVP-07 accepté et spécifications de format finalisées
2. ✅ Commandes Tauri de lecture cartographique implémentées :
   - `get_cemetery_map(cemetery_id) → CemeteryMapDTO`
   - `search_plot_by_location(request: PlotLocationRequest) → PlotMapDTO`
3. ✅ Types TypeScript générés automatiquement via specta (MVP-05A)
4. ✅ Shell frontend en place (MVP-02, MVP-06)
5. ✅ Styles de base définis (couleurs statuts)

**Pas de blocker technique avant MVP-14**, tant que :
- Les DTOs sont compilables (vérifier `cargo check`)
- Les types TypeScript sont générés (vérifier specta)
- Les commandes Tauri mockées existent (même si stub)

### 6.3 Critères métier d'acceptation

Une fois MVP-14 rendu, le plan doit :

- [ ] Afficher tous les emplacements d'un cimetière
- [ ] Colorer chaque emplacement selon son statut
- [ ] Permettre la sélection (clic) → ouvre fiche
- [ ] Afficher les info au survol (section/row/number/status)
- [ ] Supporter zoom/pan sans lag (< 100ms interaction)
- [ ] Afficher jusqu'à 500 emplacements sans freezer l'UI
- [ ] Synchroniser les changements de statut en temps réel

---

## 7. Fichiers modifiés et créations

### Fichiers à créer (Tauri backend)

```
src-tauri/src/dto/plot_map.rs          ← PlotMapDTO, CemeteryMapDTO
src-tauri/src/dto/plot_location.rs     ← PlotLocationRequest
src-tauri/src/dto/plot_stats.rs        ← PlotStatsSummaryDTO
```

### Fichiers à modifier

```
src-tauri/src/dto/mod.rs               ← Ajouter pub mod plot_map; etc.
src-tauri/src/lib.rs                   ← Exporter si nécessaire
```

**Pas de modification :**
- Schéma SQLite (plots table inchangée)
- Commandes Tauri (seront implémentées en MVP-10/11)
- Frontend (aucun rendu pour MVP-07)

---

## 8. Problèmes connus

- Aucun pour MVP-07 : c'est une spécification, pas une implémentation.
- Une fois MVP-14 implémenté, devront être validés :
  - Performance SVG pour 500+ emplacements
  - Synchronisation état + rendu en cas de changements concurrents

---

## 9. Résultats des tests

**MVP-07 n'a pas de tests executables**, car c'est un document de spécification.

Les DTOs définis seront :
- ✅ Compilables (vérifier `cargo check` après création des fichiers)
- ✅ Sérialisables (vérifier `serde`, `specta::Type`)

Les tests métier seront en MVP-14 :
- Tests unitaires : transformation coordonnées (logique → pixel)
- Tests E2E : affichage rendu → vérifier couleurs, interactions

---

## 10. Prochaines étapes

1. **MVP-09** : Implémenter repositories CRUD pour plots
2. **MVP-10/11** : Implémenter les commandes Tauri associées :
   - `get_cemetery_map(cemetery_id)` → CemeteryMapDTO
   - `search_plot_by_location(request)` → PlotMapDTO
3. **MVP-14** : Implémenter le rendu SVG/Canvas du plan interactif
4. **MVP-15** (futur) : Lier cartographie → fiches concession/défunt

---

## 11. Décisions architecturales

| Décision | Justification | Révision possible |
|----------|---------------|-------------------|
| Grille régulière virtuelle | MVP doit rester simple ; pas de SIG | Oui, post-MVP si besoin géolocalisation |
| DTOs cartographiques séparées | Clarté contrat ; évite surcharge PlotDTO | Oui, si fusion ultime de DTOs |
| Pas de stockage géométrie en base | MVP ne nécessite pas ; données logiques suffisent | Oui, pour MVP-14+ (colonnes x, y, polygon) |
| SVG recommandé pour rendu | Simplicité, interopérabilité, pas librairie | Oui, Canvas ou Leaflet light si perf insuffisante |

---

## 12. Conclusion

**MVP-07 stabilise le format cartographique MVP** en définissant :
✅ Les DTOs d'échange cartographie  
✅ La hiérarchie logique cimetière/secteur/rangée/emplacement  
✅ Le système de coordonnées simples (section, row, number)  
✅ Les contraintes de rendu pour MVP-14  
✅ Les critères d'acceptation pour débloquer le mapping

**Pas d'implémentation code ni rendu visuel** — c'est une spécification stabilisant le contrat. Le rendez-vous MVP-14 aura des données bien structurées et un format clair à consommer.

**Blocage mapping LEVÉ après cette spécification.** Le frontend et le backend peuvent maintenant procéder en parallèle.
