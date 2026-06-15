# Audit de readiness — lancement frontend et mapping

Date : 2026-06-15

## Périmètre audité

Documents lus :
- `ROADMAP.md`
- `agents/QUEUE.md`
- `agents/STATUS.md`
- `reports/dev/MVP-00.md`
- `reports/dev/MVP-01.md`
- `reports/dev/MVP-03.md`
- `reports/dev/MVP-04.md`
- `reports/dev/MVP-05.md`
- `reports/dev/MVP-05A.md`
- `reports/dev/MVP-08.md`
- `reports/qa/backend_foundation_review.md`

Commits pris en compte :
- `71a9d18` — implémentation du socle backend MVP-00 à MVP-05A
- `78d9abf` — validation QA du socle backend

## Résumé exécutif

Le backend et la QA ont effectivement stabilisé le socle nécessaire au démarrage du `frontend`.

En revanche, `mapping` reste bloqué car le lot `MVP-07` n’est toujours pas matérialisé dans les artefacts audités. Le modèle `plots` est désormais stable, mais le format cartographique MVP n’est pas encore spécifié ni validé comme lot distinct.

Le packaging `MVP-08` reste un cadrage utile mais incomplet.

## Audit frontend

### Pré requis attendus

Pour lancer `frontend`, les prérequis critiques sont :
- `MVP-00` stabilisé ;
- `MVP-01` stabilisé ;
- `MVP-05` stabilisé ;
- `MVP-05A` stabilisé ;
- cadrage QA présent pour encadrer la suite.

### Vérification des lots backend

#### MVP-00 — Structure du dépôt et conventions

Verdict : stable.

Éléments probants :
- rapport `reports/dev/MVP-00.md` passé à `✅ Stabilisé` ;
- structure Rust/Tauri en place ;
- dépendances résolues ;
- `cargo check` indiqué comme réussi ;
- revue QA confirme la conformité du socle.

#### MVP-01 — Architecture applicative desktop

Verdict : stable.

Éléments probants :
- rapport `reports/dev/MVP-01.md` passé à `✅ Stabilisé` ;
- layering implémenté (`core`, `db`, `dto`, `commands`, `errors`) ;
- `main.rs` et `lib.rs` présents ;
- 3 tests backend passent ;
- revue QA conclut `BACKEND_FOUNDATION_ACCEPTED`.

#### MVP-04 — Schéma SQLite et entités cœur

Verdict : stable pour le lancement frontend.

Éléments probants :
- rapport `reports/dev/MVP-04.md` passé à `✅ Stabilisé` ;
- migration `001_initial_schema.sql` créée ;
- 5 tables avec FK et index ;
- modèles Rust alignés ;
- test de migrations validé ;
- revue QA confirme la cohérence schéma/modèles.

#### MVP-05 — Contrats API/Tauri et DTO partagés

Verdict : stable pour démarrer le frontend.

Éléments probants :
- rapport `reports/dev/MVP-05.md` passé à `✅ Stabilisé` ;
- DTOs définis et compilables ;
- 18 commandes Tauri stubées et enregistrées ;
- gestion d’erreurs centralisée ;
- versioning documentaire posé ;
- revue QA confirme l’alignement DTOs/modèles.

Limite restante :
- commandes encore en stubs, donc le frontend peut démarrer sur le shell, le typage et l’intégration, mais pas sur des flux métier complets finalisés.

#### MVP-05A — Génération automatique des types TypeScript

Verdict : suffisamment stable pour lancer le frontend.

Éléments probants :
- rapport `reports/dev/MVP-05A.md` passé à `✅ Stabilisé (préparation pour MVP-06)` ;
- `specta` + `tauri-specta` configurés ;
- `Type` dérivé sur tous les DTOs ;
- structure d’export en place ;
- revue QA confirme la présence des prérequis de génération.

Limite restante :
- la génération automatique n’est pas encore complètement intégrée au workflow de build ; elle est préparée et exploitable, mais pas industrialisée au maximum.

### QA

#### MVP-03 — Stratégie QA

Verdict : suffisant pour encadrer le lancement frontend.

Éléments probants :
- `reports/dev/MVP-03.md` présent ;
- stratégie QA explicitée ;
- conventions de tests présentes ;
- pas de faux signal sur des tests non exécutés.

### Conclusion frontend

Le socle backend/QA est maintenant suffisamment stable pour lancer `frontend` sur :
- `MVP-02` ;
- `MVP-06` ;
- la préparation des vues en s’appuyant sur les DTOs et types partagés.

Réserve :
- ne pas présenter les commandes Tauri stubées comme des flux métier finalisés ;
- la réalisation des vues profondes dépendra toujours de `MVP-10` et `MVP-11`.

Verdict explicite :

`FRONTEND_GO`

## Audit mapping

### Pré requis attendus

Pour lancer `mapping`, il faut au minimum :
- `MVP-04` stabilisé ;
- `MVP-07` défini ;
- et, pour l’étape suivante, cohérence future avec `MVP-10`.

### Vérification des éléments disponibles

#### MVP-04 — Modèle de données emplacements

Verdict : stable.

Éléments probants :
- structure `plots` stabilisée ;
- champs métier minimaux disponibles : `cemetery_id`, `section`, `row`, `number`, `capacity`, `status` ;
- base acceptable pour concevoir un format cartographique MVP.

#### MVP-07 — Format cartographique MVP

Verdict : absent dans les artefacts audités.

Constat :
- aucun rapport `reports/dev/MVP-07.md` présent ;
- aucune spécification formelle du format cartographique MVP n’a été fournie ici ;
- aucune décision stabilisée sur la représentation du plan, des coordonnées ou des polygones n’est tracée dans les rapports lus.

### Conclusion mapping

Le mapping ne doit pas être lancé comme implémentation réelle tant que `MVP-07` n’est pas produit.

Le backend a maintenant assez stabilisé le modèle emplacement pour permettre le cadrage de `MVP-07`, mais pas pour considérer le mapping prêt à démarrer sans ce lot.

Verdict explicite :

`MAPPING_BLOCKED`

## Audit packaging

### MVP-08 — Stratégie packaging Windows/Linux

Verdict : cadrage utile, encore incomplet.

Éléments probants :
- rapport `reports/dev/MVP-08.md` toujours au statut `Initié` ;
- stratégie claire pour NSIS / AppImage / `.deb` ;
- mais aucune configuration finalisée d’artefact n’est validée dans ce rapport ;
- pas de test d’installation ;
- pas de validation machine réelle.

Conclusion :
- `MVP-08` est suffisant pour guider le packaging ;
- `MVP-08` n’est pas suffisant pour considérer le lot packaging stabilisé.

## Recommandations immédiates

1. Lancer `frontend` sur `MVP-02` puis `MVP-06` en s’appuyant sur les DTOs/types déjà stabilisés.
2. Exiger un `reports/dev/MVP-07.md` avant tout feu vert mapping.
3. Faire converger `MVP-08` vers une configuration Tauri réellement exécutable dès que `MVP-02` avance.
4. Maintenir la distinction entre :
   - socle backend stabilisé ;
   - flux métier backend complets encore à implémenter (`MVP-09`, `MVP-10`, `MVP-11`).

## Verdict final

- FRONTEND : `FRONTEND_GO`
- MAPPING : `MAPPING_BLOCKED`
