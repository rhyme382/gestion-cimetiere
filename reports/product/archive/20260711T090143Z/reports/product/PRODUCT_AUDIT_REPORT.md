# PRODUCT_AUDIT_REPORT

## objectif

Vérifier, à partir des sources du dépôt et sans faire confiance aux anciens verdicts, quelles opérations un agent de mairie peut réellement accomplir dans l'application packagée sans terminal.

## périmètre audité

Sources lues :
- `SPEC.md`, `ROADMAP.md`, `AGENTS.md`, `agents/STATUS.md`, `agents/QUEUE.md`
- pages React, layout, composants alertes, cartographie, hooks, `src/lib/tauri.ts`, types
- commandes Tauri Rust, services, migrations SQLite, schéma actuel
- tests frontend, tests Rust, tests Playwright
- rapports QA et release listés dans la demande

## méthode

Règle de décision utilisée :
- une fonctionnalité n'est retenue comme présente que si un agent municipal peut la terminer dans l'UI, sans terminal, avec une preuve crédible dans les sources lues.

Ce qui n'a pas été accepté comme preuve suffisante :
- existence d'un endpoint backend seul ;
- présence d'un écran placeholder ;
- bouton visible sans effet ;
- rapport ancien contredit par le code ou par d'autres rapports.

## constats principaux

1. Le produit actuel est majoritairement lecture seule.
2. Les parcours de saisie métier cœur ne sont pas terminés en UI.
3. La cartographie affichée est une maquette branchée sur des mocks, pas sur la base réelle.
4. La sauvegarde/restauration n'est pas fiable en UI à cause d'un contrat front/back incohérent.
5. Les alertes sont consultables, mais leur recalcul n'est pas piloté depuis l'interface.
6. Plusieurs boutons `Détails`, `Voir`, `Éditer`, `Imprimer` ou `Supprimer` sont inertes.
7. Les anciens verdicts "ready" ne résistent pas à la lecture croisée du code, des tests et des rapports release.

## verdict produit

Verdict : **prototype avancé, non alpha métier exploitable**

Un agent de mairie peut réellement :
- naviguer dans l'application ;
- consulter des concessions existantes ;
- consulter des défunts existants ;
- lancer une recherche simple ;
- consulter des alertes existantes ;
- acquitter une alerte ;
- générer un PDF simple de concession ;
- manipuler une cartographie de démonstration.

Un agent de mairie ne peut pas réellement :
- initialiser une base métier depuis l'UI ;
- créer ou gérer un cimetière ;
- créer ou gérer un emplacement ;
- créer ou gérer une concession ;
- créer ou rattacher correctement personnes, ayants droit et défunts ;
- restaurer une sauvegarde ;
- prouver un usage packagé validé sur installateur final.

## écarts probants

### UI placeholder ou non branchée

- `src/pages/CemeteriesPage.tsx` est un placeholder.
- `src/pages/ParametresPage.tsx` est un placeholder.
- `src/pages/DefuntsPage.tsx` affiche un bouton `Détails` non branché.
- `src/pages/RecherchePage.tsx` affiche des boutons `Voir` non branchés.
- `src/pages/ConcessionDetailPage.tsx` et `src/pages/DefuntDetailPage.tsx` montrent des actions sans implémentation.

### Contrats front/back incohérents

- Les helpers `create*` et `update*` de `src/lib/tauri.ts` envoient `request`, alors que les commandes Rust acceptent `req`.
- `restore_backup` côté frontend envoie `filename`, alors que la commande Rust attend `backup_filename`.
- `list_backups` renvoie des chaînes, alors que l'UI attend des objets détaillés.

### Cartographie non métier

- `src/pages/EmplacementsPage.tsx` utilise `mockCemeteryMap`.
- `src/mocks/cemetery-map.ts` pilote l'écran principal de cartographie.

### Tests et release

- `npm test -- --run` échoue actuellement faute de module `@testing-library/dom`.
- Les Playwright présents contrôlent surtout visibilité et présence d'éléments.
- Certaines specs visent `/dashboard`, route absente de `src/router.tsx`.
- Les rapports release signalent encore des artefacts packagés manquants ou en attente de workflow.

## commandes exécutées

- lecture ciblée des sources listées dans la demande ;
- `npm test -- --run`

## résultat des vérifications exécutées

### Vitest

Résultat : échec

Cause lue dans la sortie :
- module manquant `@testing-library/dom`

Effet :
- les tests frontend déclarés "passants" ne sont pas reproductibles tels quels dans l'état courant du dépôt.

## décision

Ne pas présenter ce dépôt comme "MVP prêt mairie".

Le positionnement honnête à la date de l'audit est :
- socle technique utilisable ;
- consultation partielle possible ;
- alpha métier non atteinte.

## livrables produits

- `product/FEATURE_MATRIX.md`
- `product/GAP_ANALYSIS.md`
- `product/USER_JOURNEYS.md`
- `product/ALPHA_ROADMAP.md`
- `tasks/backlog.json`

## prochaine étape recommandée

Traiter le backlog alpha en commençant par :
1. création de cimetières, emplacements, concessions et personnes en UI ;
2. correction des contrats Tauri réellement utilisés par l'interface ;
3. cartographie réelle ;
4. sauvegardes réellement exploitables ;
5. preuve d'un parcours packagé sans terminal.
