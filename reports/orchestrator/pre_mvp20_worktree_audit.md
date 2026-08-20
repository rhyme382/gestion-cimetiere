# Audit du worktree avant MVP-20

Date : 2026-06-16
Agent : orchestrator
Statut : audit documentaire uniquement

## Objet

Établir l’état réel du worktree avant lancement de `MVP-20`, lister précisément les fichiers backend modifiés, et qualifier leur origine probable parmi :

- correctif `MVP-18 PDF` ;
- reliquat non committé ;
- modification accidentelle ;
- `MVP-20` anticipé.

## Fichiers backend modifiés

### Correctif MVP-18 PDF non entièrement committé

- `Cargo.lock`

Qualification :

- contient l’ajout de `printpdf` et de ses dépendances transitive (`lopdf`, `encoding_rs`, `ttf-parser`, etc.) ;
- correspond clairement au correctif `MVP-18 PDF réel` validé ensuite par QA ;
- n’a pas été inclus dans le commit backend PDF alors qu’il accompagne logiquement `src-tauri/Cargo.toml`.

Conclusion par fichier :

- `Cargo.lock` : **appartient au correctif MVP-18 PDF**

### Reliquat non committé, non lié à MVP-20

Fichiers observés :

- `src-tauri/src/commands/alert.rs`
- `src-tauri/src/commands/burial.rs`
- `src-tauri/src/commands/cemetery.rs`
- `src-tauri/src/commands/concession.rs`
- `src-tauri/src/commands/individual.rs`
- `src-tauri/src/commands/mod.rs`
- `src-tauri/src/commands/plot.rs`
- `src-tauri/src/core/models/individual.rs`
- `src-tauri/src/core/models/mod.rs`
- `src-tauri/src/core/services/cemetery_service.rs`
- `src-tauri/src/db/connection.rs`
- `src-tauri/src/db/migrations.rs`
- `src-tauri/src/db/repositories/alert_repo.rs`
- `src-tauri/src/db/repositories/burial_repo.rs`
- `src-tauri/src/db/repositories/cemetery_repo.rs`
- `src-tauri/src/db/repositories/concession_repo.rs`
- `src-tauri/src/db/repositories/individual_repo.rs`
- `src-tauri/src/db/repositories/mod.rs`
- `src-tauri/src/db/repositories/plot_repo.rs`
- `src-tauri/src/dto/mod.rs`
- `src-tauri/src/lib.rs`
- `src-tauri/src/services/alert_service.rs`
- `src-tauri/tests/integration_alert.rs`
- `src-tauri/tests/integration_burial.rs`
- `src-tauri/tests/integration_cemetery.rs`
- `src-tauri/tests/integration_concession.rs`
- `src-tauri/tests/integration_individual.rs`
- `src-tauri/tests/integration_plot.rs`

Constats :

- les diffs inspectés sont dominés par :
  - réordonnancement d’`use`;
  - reformatage de signatures de fonctions ;
  - retours à la ligne / mise en forme de tests ;
  - légères réorganisations d’ordre de modules/export.
- aucun signal de sauvegarde/restauration locale n’apparaît ;
- aucun mot-clé ou structure liée à `MVP-20` (`backup`, `restore`, `save`, `snapshot`, archives, export DB, import DB) n’a été trouvé ;
- ces fichiers ne font pas partie du périmètre du correctif `MVP-18 PDF` validé (`pdf_service.rs`, `pdf.rs`, `main.rs`, `services/mod.rs`, `integration_pdf.rs`).

Conclusion par groupe :

- tous les fichiers listés ci-dessus : **reliquat non committé**

### Modifications accidentelles

Aucune preuve forte d’une modification accidentelle isolée n’a été relevée.

Le pattern est cohérent avec :

- un passage de formatage large (`rustfmt` / réorganisation import/ligne) ;
- ou un reliquat d’un travail intermédiaire plus large jamais committé.

Conclusion :

- **aucun fichier backend n’est classé en “modification accidentelle” avec certitude**

### MVP-20 anticipé

Recherche effectuée :

- aucune trace de logique de sauvegarde/restauration locale ;
- aucun nouveau module backend dédié ;
- aucune migration ou commande Tauri évoquant la persistance d’archives, exports ou imports ;
- aucun test backend orienté sauvegarde/restauration.

Conclusion :

- **aucun fichier backend actuel ne relève de MVP-20 anticipé**

## Fichier non backend mais lié au sujet

- `src/lib/tauri.ts`

Constat :

- ajoute `generateConcessionPdf(concession_id)` côté frontend ;
- relève du chaînage UI/backend PDF autour de MVP-19 ;
- n’est pas backend et n’entre pas dans la qualification backend demandée.

## Diagnostic global

Le worktree backend mélange deux réalités distinctes :

1. un fichier légitime manquant au commit `MVP-18` :
   - `Cargo.lock`
2. un ensemble large de reliquats non committés sans lien avec `MVP-20`, principalement du reformatage/réordonnancement :
   - commandes, repositories, modèles et tests backend

Ce mélange ne doit pas être traité par un commit unique.

## Conclusion

**SPLIT_COMMIT**

## Justification

- `MUST_COMMIT` serait trop grossier, car il agrégerait un correctif légitime (`Cargo.lock` MVP-18) et un ensemble de reliquats non qualifiés pour lancement de MVP-20.
- `MUST_RESTORE` serait excessif, car `Cargo.lock` appartient clairement au correctif PDF réel de `MVP-18`.
- `SPLIT_COMMIT` est l’option correcte :
  - extraire et traiter séparément `Cargo.lock` comme reliquat du correctif MVP-18 ;
  - examiner indépendamment le gros bloc de reformatage backend avant toute décision de commit ou restauration ;
  - ne pas lancer MVP-20 tant que cette séparation n’est pas clarifiée.

## Recommandation opérationnelle

Avant `MVP-20` :

1. isoler `Cargo.lock` et décider explicitement s’il doit compléter le correctif `MVP-18` ;
2. décider séparément du bloc de reformatage backend non committé ;
3. garder `reports/dev/MVP-19.md` et `agents/STATUS.md` alignés sur la roadmap officielle : prochain lot réel = `MVP-20` sauvegarde/restauration locale.
