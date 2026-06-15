# Rapport MVP-03 : Définir la stratégie de tests du MVP

**Date** : 2026-06-15
**Agent responsable** : QA
**Statut** : ✅ Livré
**Dépendance** : MVP-01 (architecture applicative)

---

## 1. Objectif

Définir un plan de validation systématique et reproductible couvrant les flux critiques du MVP (13 capacités) sans implémentation métier préalable. Ce plan guide la production de tests unitaires, intégration, end-to-end et validation manuelle tout au long des 5 phases de livraison.

## 2. Décisions actées

### Pyramide de tests retenue

- **Niveau 1 (Unitaires)** : Logique métier isolée, validation schéma. Vitest. Couverture ≥ 80 %.
- **Niveau 2 (Intégration)** : Contrats Tauri ↔ SQLite. Vitest + fixtures. 100 % des contrats.
- **Niveau 3 (E2E)** : Flux critiques complets Tauri → base → UI. Playwright. 8-10 flux couverts.
- **Niveau 4 (Validation manuelle)** : Aspects visuels, ergonomie, détection régression. Post-E2E par phase.

### Flux critiques couverts prioritairement

1. Création et modification de concession (formulaire → persistance → affichage) ;
2. Rattachement d'un défunt à concession ;
3. Recherche globale (requête → résultats filtrés → navigation) ;
4. Alertes d'échéance (calcul → notification → action) ;
5. Cartographie (affichage plan → sélection emplacement → lien métier) ;
6. Installation locale (Windows/Linux → setup → app opérationnelle).

### Jeux de données standardisés

**Fixture `tests/fixtures/init_mvp.sql`** :
- 1 cimetière test ;
- 3 sections avec statuts mixtes ;
- 5 concessions (dates d'échéance variées) ;
- 8 défunts (rattachés/détachés/orphelins) ;
- 2 personnes sans concession ;
- Données cohérentes, reproductibles, applicables pré-test.

### Nommage et traçabilité

- Tests identifiés : `T-<domaine>-<numéro>` (ex: `T-CONCESSION-001`) ;
- Domaines : SCHEMA, CIMETIÈRE, EMPLACEMENT, CONCESSION, PERSONNE, RECHERCHE, ALERTE, INSTALL ;
- Structure répertoires : `tests/unit/`, `tests/integration/`, `tests/e2e/`, `tests/fixtures/`, `agents/reports/` ;
- Rapports de résultats : JSON + Markdown suite à chaque exécution.

### Stack de test

| Couche | Outil | Usage |
| --- | --- | --- |
| Unitaire/Intégration | Vitest | Backend Rust, logique TypeScript, migrations |
| Frontend | React Testing Library + Vitest | Composants, hooks |
| E2E | Playwright | Flux Tauri complets |
| Fixtures | SQL + JSON | Données reproductibles |
| CI/CD | GitHub Actions | Automatisation |

### Critères d'acceptation globaux

- **Couverture unitaire** : ≥ 80 % des branches métier critiques ;
- **Tests intégration** : 100 % des contrats Tauri livrés ;
- **Tests E2E** : 100 % des flux critiques couverts ;
- **Performance** : unitaires < 5s, intégration < 30s, E2E total < 5 min ;
- **Non-régression** : blocage si anomalie détectée entre phases ;
- **Bloculaire fonctionnel** : toute anomalie métier détectée en test automatisé bloque jusqu'à correctif.

## 3. Livrables

### 1. Document de stratégie (`orchestration/qa_strategy.md`)

Contient :
- Objectif et contexte ;
- Pyramide de tests avec périmètre, outils, couverture, critères ;
- Jeux de données de test (fixtures, variantes, edge cases) ;
- Plan de couverture par domaine (tableau synthétique) ;
- Cycle de validation par phase (Phase 1-5 avec rapports attendus) ;
- Métriques de qualité (couverture, non-régression, tracabilité) ;
- Stack technique et environnements ;
- Gestion des blocages et risques résiduels ;
- Prochaines étapes post-MVP-03.

### 2. Document de conventions (`orchestration/qa_conventions.md`)

Contient :
- Structure de répertoires tests (avec arborescence complète) ;
- Nomenclature fichiers et identifiants (`T-XXXX-NNN`) ;
- Conventions Vitest (syntaxe, assertions, couverture minimale) ;
- Conventions Playwright (structure, assertions visuelles, timeouts) ;
- Conventions de données (fixture standardisée, dénomination) ;
- Format de rapports de test et traces de régression ;
- Critères d'acceptation tests (avant livraison) ;
- Intégration continue (GitHub Actions, format commit) ;
- Communication et escalade (anomalies bloquantes vs mineures) ;
- Checklist de validation par phase ;
- Ressources (liens documentation).

### 3. Rapport de livrable (`agents/reports/MVP-03.md`)

Ce fichier : résumé des décisions, livrables, dépendances, blocages, prochaines étapes.

## 4. Fichiers créés/modifiés

- ✅ Créé : `orchestration/qa_strategy.md` (stratégie détaillée, 150+ lignes) ;
- ✅ Créé : `orchestration/qa_conventions.md` (conventions, 250+ lignes) ;
- ✅ Créé : `agents/reports/MVP-03.md` (ce rapport).

## 5. Dépendances et blocages

### Dépendances respectées
- ✅ MVP-01 (architecture applicative du workspace) : structure du projet stabilisée.
- ✅ SPEC.md et ROADMAP.md : lus et intégrés.
- ✅ agents/STATUS.md : cohérent avec le statut QA.

### Aucun blocage identifié

- Stack technique retenue (Vitest + Playwright) disponible et stable ;
- Fixture SQL compatible SQLite ;
- Conventions libres de dépendance externe ;
- Prêt pour Phase 1 (noyau métier).

## 6. Problèmes connus et risques résiduels

### Phase 1 (Noyau métier)
- **Risque** : difficultés de migration ou couverture métier < 75 % ;
- **Mitigation** : fixtures appliquées d'abord, audit couverture.

### Phase 2 (Interface métier)
- **Risque** : timing flaky en E2E (network, render) ;
- **Mitigation** : timeouts explicites, waitForLoadState, marquage @flaky.

### Phase 3 (Cartographie)
- **Risque** : divergence visuelle Windows/Linux sur rendu ;
- **Mitigation** : capture d'écrans par OS, comparaison visuelle.

### Phase 4 (Documents, alertes)
- **Risque** : complexité PDF (mise en page, encodage) ;
- **Mitigation** : validation contenu et format, test sur formats courants.

### Phase 5 (Packaging)
- **Risque** : installation échoue sur poste mairie test ;
- **Mitigation** : validation complète packaging + installer, checklist d'installation.

### Acceptés pour MVP
- **Cartographie MVP** : fonctionnalités zoom/pan limitées (couverture partielle) ;
- **PDF simple** : pas de graphiques avancés (scope MVP) ;
- **Performance** : seuil > 10K lignes non garanti ;
- **Portabilité** : Windows et Linux uniquement (pas macOS) ;
- **Déviations visuelles** : UI sujette à évolution en Phase 2, validées en comparaison snapshot.

## 7. Résultats et observations

### Tests de conformité de la stratégie
- ✅ Stratégie cohérente avec pyramide des tests (4 niveaux) ;
- ✅ Flux critiques clairement identifiés (6 flux) ;
- ✅ Jeux de données standardisés reproductibles ;
- ✅ Nommage et traçabilité définis systématiquement ;
- ✅ Critères d'acceptation concrets et mesurables ;
- ✅ Stack technique alignée avec dépôt (Tauri/React/Rust/TypeScript/SQLite).

### Couverture par domaine attendue

| Domaine | Unitaires | Intégration | E2E | Validation |
| --- | --- | --- | --- | --- |
| Schéma/migrations | 3-4 | 2-3 | – | Inspection |
| Cimetières/sections | 2 | 2 | Listing + détail | Checklist UI |
| Emplacements/cartographie | 3-4 | 3-4 | Affichage + sélection | Zoom/pan/légende |
| Concessions | 4-5 | 4-5 | Création/modif/suppression | Formulaires/tri |
| Personnes/défunts | 3-4 | 3-4 | Rattachement/recherche | Fiche complète |
| Recherche globale | 2 | 2 | Requête/résultats | Filtrages/tri |
| Alertes d'échéance | 3 | 2 | Notification/action | Dashboard |
| Installation packaging | – | – | 1/OS | Procédure Windows/Linux |
| **Totaux** | **20-25** | **20-25** | **8-10 flux** | **Par domaine** |

### Impact sur roadmap

- **MVP-03 validé** → QA prêt à lancer Phase 1 (MVP-24: fixtures + tests backend) ;
- **Dépendances en aval** : MVP-24, MVP-25, MVP-26, MVP-27 (tests phases 1-5 et audit final) ;
- **Pas de blocage** sur lancement simultané autres agents (frontend, backend, mapping, packaging).

## 8. Prochaines étapes

### Immédiat (Fin MVP-03)
- ✅ Stratégie et conventions validées et livrées ;
- ✅ Structure de répertoires tests créée lors de Phase 1 ;
- ✅ Fixture `init_mvp.sql` appliquée avant tests Phase 1.

### Phase 1 (Noyau métier MVP — MVP-04 à MVP-09)
- Lancer `backend` sur MVP-04 (schéma SQLite) ;
- QA suit : créer tests unitaires/intégration sur schéma (MVP-24) ;
- Valider migrations et entités côté backend.

### Phase 2 (Interface métier MVP — MVP-10 à MVP-13)
- Backend expose commandes Tauri ;
- QA suit : créer tests E2E (MVP-25) + validation UI (checklist) ;
- Déployer composants React et écrans.

### Phase 3+ (Cartographie, documents, packaging)
- Progression selon roadmap phases 3-5 ;
- QA exécute à chaque phase selon pyramide définie ;
- Audit final (MVP-27) : rapport de readiness complet.

## 9. Documentation de référence

- **SPEC.md** : spécifications métier et besoins mairie ;
- **ROADMAP.md** : phases et dépendances du MVP ;
- **agents/STATUS.md** : suivi global agents et blocages ;
- **orchestration/qa_agent.md** : mission QA agent ;
- **orchestration/qa_strategy.md** : stratégie de tests (détail) ;
- **orchestration/qa_conventions.md** : conventions de développement (détail).

---

## ✅ Critère de done

- [x] Stratégie de tests MVP définie et documentée ;
- [x] Conventions QA écrites et applicables ;
- [x] Fixtures de test spécifiées (reproducibles) ;
- [x] Flux critiques identifiés (6 flux) ;
- [x] Stack technique alignée (Vitest + Playwright) ;
- [x] Critères d'acceptation concrets ;
- [x] Blocages identifiés et mitigations prévues ;
- [x] Prochaines étapes claires (MVP-24, MVP-25, MVP-26, MVP-27).

MVP-03 est **LIVRÉ**. QA prêt pour Phase 1.
