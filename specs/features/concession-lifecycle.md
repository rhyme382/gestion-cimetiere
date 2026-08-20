# FEATURE-CONCESSION-LIFECYCLE-001
# Cycle de vie de base d’une concession funéraire

## 1. Objectif

Permettre à un agent communal de :

- consulter la liste des concessions ;
- rechercher et filtrer les concessions ;
- créer une concession ;
- consulter son dossier détaillé ;
- modifier ses informations ;
- connaître immédiatement son état et son échéance.

Cette fonctionnalité constitue le premier socle métier exploitable de gestion des concessions.

Elle doit s’intégrer à l’architecture existante du logiciel de gestion de cimetières.

## 2. Périmètre fonctionnel

### Inclus

- persistance SQLite ;
- modèle métier Rust ;
- commandes Tauri ;
- contrats TypeScript ;
- liste des concessions ;
- formulaire de création ;
- formulaire de modification ;
- page de détail ;
- recherche simple ;
- filtres d’état ;
- calcul automatique de la date d’échéance ;
- calcul automatique de l’état de la concession ;
- validations métier ;
- tests Rust ;
- tests TypeScript/Vitest ;
- test Playwright du parcours nominal ;
- rapport de développement pour chaque tâche.

### Exclus

Ne pas implémenter dans cette feature :

- renouvellement d’une concession ;
- conversion ou prolongation de durée ;
- paiement ou facturation ;
- génération d’actes PDF ;
- signature électronique ;
- télétransmission ;
- reprise d’une concession ;
- procédure d’abandon ;
- gestion des ayants droit ;
- rattachement détaillé des défunts ;
- import de données historiques ;
- archivage documentaire ;
- notifications automatiques ;
- cartographie des emplacements.

Ces sujets feront l’objet de fonctionnalités distinctes.

## 3. Terminologie métier

Une concession représente le droit accordé par la commune d’utiliser un emplacement funéraire pendant une durée déterminée ou, si la réglementation et les données existantes le permettent, de manière perpétuelle.

Dans cette première version, une concession doit obligatoirement être rattachée à :

- un cimetière existant ;
- un emplacement existant.

## 4. Données d’une concession

Chaque concession possède au minimum les informations suivantes :

- identifiant technique ;
- numéro de concession ;
- identifiant du cimetière ;
- identifiant de l’emplacement ;
- nom du concessionnaire principal ;
- prénom du concessionnaire principal ;
- adresse postale facultative ;
- code postal facultatif ;
- commune facultative ;
- date de début ;
- durée ;
- date d’échéance calculée ;
- type de concession ;
- état calculé ;
- notes facultatives ;
- date de création ;
- date de dernière modification.

## 5. Numéro de concession

Le numéro de concession est une chaîne métier saisie ou confirmée par l’agent.

Règles :

- il est obligatoire ;
- il est unique ;
- il est conservé tel qu’il est saisi après suppression des espaces inutiles en début et fin ;
- deux numéros ne peuvent pas être identiques sans distinction de casse si le dépôt applique déjà cette convention ;
- une erreur claire doit être retournée en cas de doublon.

Ne pas créer dans cette feature de générateur complexe de numérotation communale.

## 6. Type de concession

Les types autorisés sont :

- TEMPORAIRE ;
- TRENTENAIRE ;
- CINQUANTENAIRE ;
- PERPETUELLE.

Le dépôt peut réutiliser une énumération métier existante si elle est compatible.

## 7. Durée

La durée doit être cohérente avec le type :

- TEMPORAIRE : durée en années strictement positive ;
- TRENTENAIRE : 30 ans ;
- CINQUANTENAIRE : 50 ans ;
- PERPETUELLE : aucune date d’échéance.

Si le logiciel possède déjà des conventions de durée différentes ou plus précises, elles doivent être documentées et conservées lorsqu’elles sont compatibles avec cette spécification.

Pour les concessions temporaires, la durée doit être comprise entre 1 et 99 ans.

## 8. Calcul de la date d’échéance

Pour une concession non perpétuelle :

- la date d’échéance est calculée automatiquement à partir de la date de début et de la durée ;
- elle ne doit pas être saisie indépendamment par l’utilisateur ;
- le calcul doit gérer correctement les années bissextiles ;
- le backend Rust constitue la source de vérité du calcul.

Pour une concession perpétuelle :

- la date d’échéance est absente ;
- l’interface affiche clairement « Perpétuelle ».

## 9. État calculé

L’état d’une concession est calculé automatiquement.

Valeurs :

- ACTIVE ;
- ECHEANCE_PROCHE ;
- EXPIREE ;
- PERPETUELLE.

Règles :

- PERPETUELLE si le type est perpétuel ;
- EXPIREE si la date d’échéance est antérieure à la date courante ;
- ECHEANCE_PROCHE si l’échéance intervient dans les 12 prochains mois inclus ;
- ACTIVE dans les autres cas.

L’état ne doit pas être saisi ou modifié manuellement.

Le backend Rust constitue la source de vérité.

Les tests doivent utiliser une date de référence injectable ou déterministe afin de ne pas devenir instables avec le temps.

## 10. Création d’une concession

L’écran de création permet de saisir :

- numéro de concession ;
- cimetière ;
- emplacement ;
- nom du concessionnaire ;
- prénom du concessionnaire ;
- adresse ;
- code postal ;
- commune ;
- date de début ;
- type ;
- durée lorsque nécessaire ;
- notes.

Validations obligatoires :

- numéro non vide ;
- cimetière existant ;
- emplacement existant ;
- emplacement non déjà occupé par une concession active incompatible, selon les règles existantes du dépôt ;
- nom du concessionnaire non vide ;
- date de début valide ;
- type valide ;
- durée cohérente ;
- numéro unique.

En cas d’erreur :

- aucune donnée partielle ne doit être enregistrée ;
- l’erreur doit être structurée côté backend ;
- le formulaire doit afficher un message compréhensible ;
- les valeurs saisies doivent rester présentes.

## 11. Modification

L’agent peut modifier :

- numéro de concession ;
- concessionnaire principal ;
- coordonnées ;
- date de début ;
- type ;
- durée ;
- notes ;
- rattachement à l’emplacement si l’architecture métier existante l’autorise.

Après modification :

- la date d’échéance est recalculée ;
- l’état est recalculé ;
- la date de dernière modification est mise à jour.

L’identifiant technique et la date de création ne sont jamais modifiables.

## 12. Liste des concessions

La page de liste affiche au minimum :

- numéro ;
- concessionnaire principal ;
- cimetière ;
- emplacement ;
- type ;
- date de début ;
- échéance ou « Perpétuelle » ;
- état.

Fonctions :

- tri cohérent avec les composants existants ;
- recherche sur numéro, nom et prénom ;
- filtre par état ;
- filtre par cimetière si l’architecture existante le permet simplement ;
- accès à la page de détail ;
- bouton de création.

La liste doit gérer :

- chargement ;
- absence de résultat ;
- erreur backend ;
- rafraîchissement.

## 13. Page de détail

La page de détail affiche toutes les informations connues de la concession.

Elle doit notamment rendre visibles :

- le numéro ;
- l’identité du concessionnaire ;
- le cimetière ;
- l’emplacement ;
- le type ;
- la durée ;
- la date de début ;
- l’échéance ;
- l’état ;
- les notes ;
- les dates de création et modification.

Elle propose une action de modification.

Aucune action de suppression n’est demandée dans cette feature.

## 14. Interface

L’interface doit :

- réutiliser les composants et styles existants ;
- rester cohérente avec les pages actuelles ;
- être utilisable à la souris et au clavier ;
- afficher des libellés en français ;
- éviter les composants ou bibliothèques supplémentaires sans nécessité ;
- ne pas introduire un second système de formulaires ou de validation si le dépôt possède déjà une solution.

## 15. Persistance SQLite

La conception doit inspecter le schéma existant avant toute migration.

Règles :

- réutiliser les tables et colonnes existantes lorsqu’elles correspondent au besoin ;
- créer une migration uniquement si nécessaire ;
- préserver les données existantes ;
- prévoir les contraintes d’unicité et d’intégrité utiles ;
- ne jamais supprimer silencieusement de données ;
- les migrations doivent être testées ;
- les accès doivent suivre les conventions actuelles du dépôt.

## 16. Backend Rust / Tauri

Le backend doit fournir les opérations nécessaires, conceptuellement équivalentes à :

- list_concessions ;
- get_concession ;
- create_concession ;
- update_concession.

Les noms exacts doivent respecter les conventions du dépôt.

Le backend doit :

- valider toutes les règles métier ;
- calculer l’échéance ;
- calculer l’état ;
- retourner des erreurs structurées ;
- éviter les panic sur erreur utilisateur ou SQLite attendue ;
- utiliser des transactions pour les créations et modifications ;
- ne jamais faire confiance aux états ou échéances calculés par le frontend.

## 17. Contrats TypeScript

Le frontend doit disposer de types explicites pour :

- concession ;
- création ;
- modification ;
- filtres ;
- type de concession ;
- état de concession ;
- erreurs utiles.

Ne pas introduire de `any` implicite.

Les noms et formats doivent rester cohérents avec les DTO Rust et les conventions Tauri existantes.

## 18. Tests Rust

Couvrir au minimum :

- création nominale ;
- numéro obligatoire ;
- numéro dupliqué ;
- cimetière inexistant ;
- emplacement inexistant ;
- durée temporaire invalide ;
- calcul trentenaire ;
- calcul cinquantenaire ;
- concession perpétuelle sans échéance ;
- état actif ;
- échéance proche ;
- état expiré ;
- modification et recalcul ;
- erreur SQLite contrôlée si pertinente ;
- migration ou schéma si modifié.

Les tests de dates doivent être déterministes.

## 19. Tests TypeScript / Vitest

Couvrir au minimum :

- typage et appel du client Tauri ;
- rendu de la liste ;
- état vide ;
- état d’erreur ;
- filtres ou recherche ;
- formulaire nominal ;
- erreurs de validation ;
- conservation des valeurs après erreur ;
- page de détail ;
- affichage d’une concession perpétuelle ;
- affichage des différents états.

Les tests doivent viser les composants réels du produit.

## 20. Test Playwright

Créer au minimum un parcours nominal Chromium :

1. ouvrir la liste des concessions ;
2. lancer la création ;
3. remplir le formulaire ;
4. enregistrer ;
5. constater le retour ou l’accès au détail ;
6. vérifier le numéro ;
7. vérifier le concessionnaire ;
8. vérifier le type ;
9. vérifier l’échéance calculée ;
10. vérifier l’état affiché ;
11. revenir à la liste ;
12. retrouver la concession créée.

Le test doit utiliser les mécanismes E2E existants du dépôt.

Il ne doit pas dépendre d’une base de production.

Il doit être reproductible.

## 21. Qualité et non-régression

Les tâches doivent utiliser :

- des validations ciblées ;
- les quality gates globales ;
- la baseline avant/après ;
- le contrôle des chemins ;
- la revue Codex ;
- les rapports de tâche.

Aucune tâche ne doit modifier les fichiers d’une tâche suivante.

Les artefacts générés ne doivent pas être committés.

## 22. Critères d’acceptation globaux

La feature est acceptée si :

1. une concession peut être créée depuis l’interface ;
2. elle est persistée dans SQLite ;
3. son échéance est calculée correctement ;
4. son état est calculé correctement ;
5. elle apparaît dans la liste ;
6. son détail est consultable ;
7. elle peut être modifiée ;
8. les modifications recalculent échéance et état ;
9. les erreurs métier sont affichées clairement ;
10. les tests Rust ciblés réussissent ;
11. les tests TypeScript ciblés réussissent ;
12. le parcours Playwright nominal réussit ;
13. aucune nouvelle régression n’est détectée par la baseline ;
14. toutes les tâches sont approuvées et intégrées ;
15. le workflow atteint le statut COMPLETED.

## 23. Contraintes d’implémentation

- inspecter le dépôt avant de planifier ;
- conserver l’architecture existante lorsqu’elle est saine ;
- ne pas ajouter de dépendance sans justification ;
- ne pas créer de nouvelle architecture générique ;
- ne pas modifier les fonctionnalités hors périmètre ;
- utiliser des chemins relatifs au dépôt ;
- produire des tâches petites et testables ;
- attribuer chaque exigence à une tâche propriétaire principale ;
- utiliser les preuves des dépendances intégrées sans exiger leur réimplémentation ;
- produire un rapport exact pour chaque tâche.
