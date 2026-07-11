# Gap Analysis

Date d'audit : 2026-07-11

## Résumé

L'écart principal n'est pas un manque de backend. L'écart principal est l'absence de parcours métier réellement exploitables depuis l'interface packagée.

Le produit revendique un MVP complet, mais la preuve lue dans le dépôt montre plutôt :
- un backend CRUD partiel ;
- une UI majoritairement lecture seule ;
- plusieurs écrans placeholder ;
- des tests et rapports qui valident la présence d'écrans plus que l'opérabilité métier réelle.

## Gaps critiques

### G1. Aucune chaîne de saisie métier complète

Impact :
- un agent ne peut pas créer un cimetière ;
- il ne peut pas créer un emplacement ;
- il ne peut pas créer une concession ;
- il ne peut pas ajouter un concessionnaire, un ayant droit ou un défunt depuis l'application.

Preuves :
- `src/pages/CemeteriesPage.tsx` est un placeholder ;
- `src/pages/ConcessionsPage.tsx` ne contient ni formulaire ni bouton de création ;
- `src/pages/DefuntsPage.tsx` ne contient ni création ni édition ;
- les hooks `create*` existent, mais aucune vue ne les déclenche.

Conséquence produit :
- impossible de démarrer une exploitation réelle dans une mairie vide de données.

### G2. Cartographie non connectée au réel

Impact :
- l'écran Emplacements ne reflète pas les données SQLite ;
- la localisation d'une concession ou d'un défunt n'est pas fiable ;
- la navigation carte -> fiche métier n'est pas implémentée.

Preuves :
- `src/pages/EmplacementsPage.tsx` consomme `mockCemeteryMap` ;
- `src/mocks/cemetery-map.ts` contient tout le plan affiché ;
- aucun hook `usePlots` ou `useCemeteries` n'alimente cet écran.

Conséquence produit :
- le module central annoncé dans le cahier des charges n'est pas opérationnel pour une mairie.

### G3. Sauvegardes UI cassées par contrat front/back incohérent

Impact :
- la liste des sauvegardes n'est pas exploitable ;
- la restauration ne peut pas fonctionner correctement depuis l'UI.

Preuves :
- `src-tauri/src/commands/backup.rs` renvoie `Vec<String>` pour `list_backups` ;
- `src/hooks/useBackups.ts` attend des objets `{ filename, path, size, created_at }` ;
- `src/pages/SauvegardesPage.tsx` affiche `backup.filename` et `backup.created_at` ;
- `src/hooks/useBackups.ts` invoque `restore_backup` avec `{ filename }` alors que la commande attend `backup_filename`.

Conséquence produit :
- la fonctionnalité de sauvegarde/restauration ne répond pas au besoin de sécurité d'une mairie.

### G4. Alertes non pilotées par l'interface

Impact :
- les alertes peuvent rester à zéro même si des concessions sont proches d'échéance ;
- l'agent n'a aucun moyen UI de recalculer l'état.

Preuves :
- `refresh_alerts` existe côté backend et hook ;
- aucune page ne l'appelle ;
- le dashboard affiche en plus "Alertes actives" à `—`.

Conséquence produit :
- centre d'alertes visible, mais non fiable en exploitation.

### G5. Recherche et navigation incomplètes

Impact :
- la recherche n'ouvre pas les fiches depuis les résultats ;
- la liste des défunts n'ouvre pas la fiche via son bouton `Détails` ;
- les recherches successives peuvent rester figées.

Preuves :
- boutons `Voir` de `src/pages/RecherchePage.tsx` sans `navigate` ;
- bouton `Détails` de `src/pages/DefuntsPage.tsx` sans `navigate` ;
- `src/hooks/useQuery.ts` ne dépend que de `enabled`, pas des paramètres de requête.

Conséquence produit :
- un agent ne peut pas mener un parcours fluide "rechercher -> ouvrir -> agir".

### G6. Actions affichées mais non branchées

Impact :
- faux sentiment de complétude ;
- risque de déception immédiate lors d'un test mairie.

Preuves :
- boutons `Éditer`, `Imprimer`, `Supprimer` dans `src/pages/ConcessionDetailPage.tsx` sans handler métier ;
- mêmes boutons dans `src/pages/DefuntDetailPage.tsx` ;
- page Paramètres explicitement annoncée comme future.

Conséquence produit :
- l'interface montre des capacités que l'utilisateur ne peut pas réellement exercer.

### G7. Modèle de données trop réduit pour le cahier des charges

Impact :
- impossible de stocker les informations administratives clés ;
- impossible de gérer droits, documents, procédures, journal d'audit, import, statistiques avancées.

Preuves :
- schéma SQLite actuel limité à `cemeteries`, `plots`, `concessions`, `individuals`, `burials`, `alerts` ;
- absence de tables `documents`, `audit_log`, `users`, `settings`, `reclaim_procedure`, `imports`.

Conséquence produit :
- l'application couvre une sous-partie du besoin métier.

### G8. Preuves QA/release insuffisantes ou contredites par les sources

Impact :
- les anciens verdicts "ready" ne peuvent pas être retenus comme preuves produit.

Preuves :
- `reports/qa/mvp26_e2e_review.md` dit explicitement que l'E2E réel n'était pas exécuté à la date de cet audit ;
- les tests Playwright actuels vérifient surtout présence et visibilité ;
- plusieurs assertions ciblent `/dashboard` alors que la route réelle est `/` ;
- `npm test -- --run` échoue dans l'état actuel faute de module `@testing-library/dom` ;
- `reports/release/pilot_v0.1_artifacts_report.md` signale des artefacts packagés manquants ;
- `reports/release/pilot_v0.1_release_validation.md` attend encore le déclenchement du workflow.

Conséquence produit :
- aucune base solide pour affirmer qu'un agent municipal peut travailler sur une build installée.

## Gaps majeurs

### G9. PDF utile mais très en deçà du besoin administratif

Le PDF actuel génère une fiche concession simple.

Limites lues :
- pas de modèles personnalisables ;
- pas d'historique documentaire ;
- pas de titulaire réellement injecté ;
- les défunts sont listés par identifiants d'individus, pas par identité lisible.

Preuves :
- commentaire explicite dans `src-tauri/src/commands/pdf.rs` ;
- génération dans `src-tauri/src/services/pdf_service.rs`.

### G10. Packaging municipal non prouvé

État lu :
- binaire Linux produit dans un rapport ;
- AppImage et `.deb` manquants dans un autre rapport ;
- workflow GitHub annoncé prêt mais pas déclenché ;
- stockage SQLite prévu en chemin relatif `gestion_cimetiere.db`, sans usage des répertoires applicatifs OS.

Conséquence :
- l'usage réel sans terminal sur poste mairie reste non prouvé, et potentiellement fragile.

## Conclusion

Le projet ne doit pas être repositionné comme "MVP complet prêt mairie".

La lecture des sources montre plutôt un socle technique exploitable pour entrer en phase alpha, à condition de :
- terminer les parcours CRUD essentiels ;
- connecter la cartographie et les associations métier ;
- réparer sauvegardes, recherche et alertes ;
- produire une preuve de packaging réellement installable et testée.
