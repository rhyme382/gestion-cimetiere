# Stratégie de tests MVP

Date : 2026-06-15
Agent QA responsable : MVP-03

## Objectif

Définir un plan de validation systématique et reproductible couvrant les flux critiques du MVP avec une couverture progressive, sans implémentation métier préalable.

## Contexte

Le MVP couvre 13 capacités essentielles pour un premier poste mairie local (Tauri + React + SQLite). La validation doit couvrir :
- fonctionnalité métier ;
- non-régression entre phases ;
- performance et stabilité ;
- portabilité Windows/Linux.

Chaque tâche MVP doit générer un rapport d'audit tracé.

## Pyramide de tests

### Niveau 1 : Tests unitaires (socle)

**Périmètre** : briques métier isolées, logique métier, calculs, transformations de données.

**Outils** : Vitest pour le backend Rust et TypeScript.

**Couverture minimale** :
- Entités SQLite (validation des schémas, contraintes, migrations) ;
- Logique métier métier (calcul d'alertes d'échéance, recherche, validation de saisie) ;
- Conversions DTO (Rust ↔ TypeScript).

**Critères d'acceptation** :
- Couverture ≥ 80 % des fonctions critiques ;
- Temps d'exécution < 5 secondes par suite ;
- Tests reproductibles sur toute environnement (Windows/Linux).

### Niveau 2 : Tests d'intégration (contrats)

**Périmètre** : interaction Tauri + base de données, flux API, contrats entre backend et frontend.

**Outils** : Vitest avec fixtures SQLite en mémoire ou base test transitoire.

**Couverture minimale** :
- Commandes Tauri pour cimetières, emplacements, concessions, personnes, défunts ;
- Cycles de création/modification/suppression sur chaque entité ;
- Transactions et cohérence multi-table ;
- Gestion des erreurs (contraintes, validations).

**Critères d'acceptation** :
- Tous les contrats d'échange MVP versionnés et testés ;
- Pas de fuite mémoire (base test nettoyée entre tests) ;
- Temps d'exécution < 30 secondes par suite.

### Niveau 3 : Tests end-to-end (flux critiques)

**Périmètre** : parcours utilisateurs complets du poste mairie, depuis Tauri jusqu'à base et retour.

**Outils** : Playwright avec capture d'écran et assertions d'interface.

**Flux couverts prioritairement** :
1. **Création et modification de concession** : saisie formulaire → validation → persistance → affichage liste ;
2. **Rattachement d'un défunt** : sélection concession → ajout défunt → vérification cohérence ;
3. **Recherche globale** : requête → résultats filtrés → navigation vers fiche ;
4. **Alertes d'échéance** : calcul → notification → action utilisateur ;
5. **Cartographie** : affichage plan → sélection emplacement → lien vers concession ;
6. **Installation locale** : install Windows/Linux → premiers écrans → base de données vierge.

**Critères d'acceptation** :
- Chaque flux testé au minimum une fois par environnement (Windows/Linux) ;
- Assertions visuelles (éléments présents, ordre, valeurs) ;
- Gestion des edge cases (recherche vide, emplacement indisponible, etc.) ;
- Temps total < 5 minutes par environnement.

### Niveau 4 : Validation manuelle ciblée

**Périmètre** : aspect visuels, ergonomie, comportement hors scénarios de test, détection de régression visuelle.

**Processus** :
- Exécution sur poste mairie test (Windows et Linux) ;
- Checklist d'inspection par domaine (dashboard, listes, fiches, cartographie) ;
- Capture d'écran en cas de dérive par rapport aux spécifications UI ;
- Signalement de blocages ou risques résiduel.

**Critères d'acceptation** :
- Validation post-E2E avant livraison de phase ;
- Rapport incluant capture d'écrans et liste des déviations.

## Jeux de données de test

### Données minimales (fixtures)

**Base de test standardisée** :
- 1 cimetière test (Cimetière Municipal) ;
- 3 sections d'emplacements (A, B, C) avec statuts mixtes (libre, occupé, réservé) ;
- 5 concessions test (propriétaires variés, dates d'échéance proches et lointaines) ;
- 8 défunts test (rattachés/détachés, dates variées) ;
- 2 personnes test sans concession ;
- 1 défunt test sans concession (anomalie volontaire pour régression).

**Format** :
- Script `tests/fixtures/init_mvp.sql` : exécuté avant chaque suite de test ou manuellement pour validation ;
- Données cohérentes avec le schéma MVP (migrations initialisées) ;
- Identifiants reproductibles (fixture réapplicable).

### Variantes de test

- **Scénario nominal** : données valides, parcours heureux ;
- **Limite haute** : 500 concessions, 2000 défunts, recherche sur 10000 enregistrements ;
- **Anomalies** : défunts orphelins, emplacements sans section, concessions expirées sans réactivation ;
- **Edge cases** : caractères spéciaux en saisie (accents, apostrophes), identifiants en doublon (détection), dates historiques/futures.

## Plan de couverture par domaine

| Domaine | Tests unitaires | Tests intégration | Tests E2E | Validation manuelle |
| --- | --- | --- | --- | --- |
| Schéma SQLite et migrations | 3-4 tests | 2-3 tests | – | Inspection |
| Cimetières et sections | 2 tests | 2 tests | Listing + détail | Checklist UI |
| Emplacements et cartographie | 3-4 tests | 3-4 tests | Affichage plan + sélection | Drag/zoom, légende |
| Concessions | 4-5 tests | 4-5 tests | Création, modification, suppression | Formulaires, tri |
| Personnes et défunts | 3-4 tests | 3-4 tests | Rattachement, recherche | Fiche complète |
| Recherche globale | 2 tests | 2 tests | Requête et résultats | Filtrages, tri |
| Alertes d'échéance | 3 tests | 2 tests | Notification et action | Dashboard alert |
| Installation packaging | – | – | 1 test par OS | Procédure complète |
| **Totaux** | **20-25** | **20-25** | **8-10 flux** | **Par domaine** |

## Cycle de validation par phase

### Phase 1 (Noyau métier MVP)
- **Tests visés** : unitaires + intégration sur schéma, migrations, entités ;
- **Rapports attendus** : couverture unitaire, résultats migrations, absence de fuite mémoire ;
- **Blocage** : si couverture < 75 % ou régression détectée.

### Phase 2 (Interface métier MVP)
- **Tests visés** : E2E sur dashboard, listes, fiches ; unitaires UI (composants React) ;
- **Rapports attendus** : couverture E2E, capture d'écrans, temps de chargement ;
- **Blocage** : si E2E échoue ou temps > seuil.

### Phase 3 (Cartographie MVP)
- **Tests visés** : E2E cartographie, unitaires rendu ;
- **Rapports attendus** : zoom/pan, sélection emplacement, cohérence avec données ;
- **Blocage** : si affichage = dérive visuelle significative.

### Phase 4 (Documents, alertes, sauvegarde)
- **Tests visés** : E2E alertes, PDF, sauvegarde/restauration ;
- **Rapports attendus** : contenu PDF, déclenchement alertes, intégrité restauration ;
- **Blocage** : si PDF mal formé ou restauration corrompt.

### Phase 5 (Packaging et validation finale)
- **Tests visés** : E2E complet, validation manuelle poste mairie, installations Windows/Linux ;
- **Rapports attendus** : audit QA final, liste des déviations acceptées, résumé des risques résiduels ;
- **Blocage** : si installation échoue ou flux critique en régression.

## Métriques de qualité

### Couverture minimale acceptée

- **Unitaire** : ≥ 80 % des branches métier critiques ;
- **Intégration** : 100 % des contrats Tauri livrés ;
- **E2E** : 100 % des flux critiques identifiés.

### Critères de non-régression

- **Zéro** blocage fonctionnel entre phases ;
- **Zéro** anomalie sécurité (injection SQL, XSS) ;
- **Performance** : tous les tests < seuils définis (unitaire 5s, intégration 30s, E2E 5min).

### Tracabilité

- Chaque test génère un identifiant unique (`T-<domaine>-<n>`) ;
- Chaque anomalie détectée génère un ticket traçable ;
- Rapport d'exécution: date, version du code, taux de passage, durée, anomalies, impact.

## Outils et infrastructure

### Stack de test

| Couche | Outil | Usage |
| --- | --- | --- |
| Unitaire/Intégration backend | Vitest (ou cargo test) | Logique Rust, migrations |
| Unitaire/Intégration frontend | Vitest + React Testing Library | Composants React, hooks |
| E2E | Playwright | Flux Tauri complets |
| Fixtures | SQL + JSON | Données de test reproductibles |
| CI/CD | GitHub Actions | Exécution automatique |
| Rapports | Markdown + captures | Documentation des résultats |

### Environnements de test

- **Local** : Windows 11 et Linux (Ubuntu 22.04) avec Tauri runtime ;
- **CI** : pipelines GitHub Actions pour chaque commit/PR (minimum Windows et Linux) ;
- **Validation** : poste mairie test avec données de transition possibles.

## Gestion des blocages et risques résiduels

### Blocages de régression

- Toute anomalie fonctionnelle détectée en test automatisé est **bloquante** jusqu'à correctif ;
- Toute déviation visuelle majeure (UI non-conforme à spec) est **bloquante** en Phase 2+ ;
- Toute faille de sécurité détectée est **bloquante** immédiatement.

### Risques résiduels acceptés

- **Cartographie MVP** : fonctionnalité de zoom/pan limitée (MVP simple) ;
- **PDF simple** : pas de graphiques avancés (MVP) ;
- **Recherche** : pas de full-text search avancé (MVP) ;
- **Performance** : seuil d'optimisation à > 10K lignes non garanti (MVP) ;
- **Portabilité** : Windows et Linux uniquement (pas macOS).

Ces risques seront documentés dans le rapport final (MVP-27).

## Livrable attendu pour MVP-03

1. **Ce document** : stratégie validée ;
2. **orchestration/qa_conventions.md** : conventions de nommage, d'organisation et d'exécution ;
3. **agents/reports/MVP-03.md** : rapport de synthèse avec décisions actées et prochaines étapes.

### Prochaines étapes (post-MVP-03)

- **MVP-01 stabilisé** : cadrer les fixtures et valider schéma de test ;
- **Phase 1** : implémenter les tests unitaires et intégration sur noyau métier ;
- **Phase 2+** : progresser sur E2E et validation manuelle.
