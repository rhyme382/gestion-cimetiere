# FEATURE-FP-001 — Référentiel communal et fiches cimetières

## Contexte

Le logiciel doit pouvoir gérer une commune et un ou plusieurs cimetières réels. Cette fonctionnalité est la racine du chemin critique produit : elle conditionne la hiérarchie spatiale des emplacements (`FP-004`), puis le cycle de vie des concessions (`FP-010` à `FP-012`).

Le dépôt contient déjà un socle de consultation des cimetières et des développements liés aux concessions. L’implémentation doit donc commencer par inventorier et réutiliser les modèles, migrations, DTO, commandes Tauri, hooks, pages et tests existants. Aucune fonctionnalité déjà opérationnelle ne doit être recréée ou remplacée sans nécessité démontrée.

## Objectif utilisateur

En tant qu’agent de mairie, je peux enregistrer l’identité administrative de ma commune, puis créer, consulter et modifier plusieurs fiches cimetières depuis l’application, sans terminal.

## Périmètre

- référentiel d’une commune gestionnaire ;
- identité administrative minimale de la commune ;
- gestion de plusieurs cimetières rattachés à cette commune ;
- création, consultation et modification des fiches cimetières ;
- validation métier et messages d’erreur lisibles ;
- compatibilité des données existantes et absence de régression sur les écrans utilisant les cimetières ;
- tests Rust, TypeScript et parcours E2E pertinents.

## Hors périmètre

- métadonnées documentaires riches des cimetières : horaires, règlement, plans, photos et notes (`FP-003`) ;
- hiérarchie sections, carrés, rangées et emplacements (`FP-004`) ;
- espaces cinéraires ;
- paramétrage communal transversal des alertes, documents et cartographie (`FP-079` à `FP-081`) ;
- import massif et synchronisation avec un service externe.

## Exigences fonctionnelles

### R1 — Inventaire et compatibilité du socle existant

L’implémentation doit identifier les structures existantes relatives aux communes et cimetières, conserver les contrats déjà utilisés et prévoir une migration compatible avec les bases existantes.

Critères d’acceptation :

1. Un inventaire traçable indique les modèles, tables, migrations, commandes Tauri, DTO, hooks, pages et tests réutilisés ou modifiés.
2. L’ouverture d’une base existante reste possible après migration sans perte des cimetières enregistrés.
3. Les commandes et écrans existants qui consomment un identifiant de cimetière continuent de fonctionner.

### R2 — Référentiel communal

Le système doit conserver une commune gestionnaire avec une identité administrative minimale et validée.

Champs minimaux :

- nom officiel ;
- code INSEE sur cinq caractères ;
- code postal ;
- adresse administrative facultative ;
- téléphone et courriel facultatifs.

Critères d’acceptation :

1. L’agent peut enregistrer le nom officiel, le code INSEE et le code postal de la commune.
2. Le code INSEE est obligatoire, composé exactement de cinq caractères alphanumériques et normalisé en majuscules.
3. Le courriel facultatif est validé lorsqu’il est renseigné.
4. Une erreur de validation est affichée en français et aucune donnée invalide n’est persistée.
5. La lecture du référentiel renvoie les mêmes valeurs après redémarrage de l’application.

### R3 — Fiches cimetières

Chaque cimetière doit être rattaché à la commune gestionnaire et posséder une identité exploitable par les autres domaines métier.

Champs minimaux :

- nom unique au sein de la commune ;
- adresse facultative ;
- capacité indicative facultative, entière et positive ou nulle ;
- état actif/inactif ;
- date de création et date de dernière modification techniques.

Critères d’acceptation :

1. L’agent peut créer plusieurs cimetières rattachés à la commune.
2. Deux cimetières actifs ne peuvent pas porter le même nom après normalisation des espaces et de la casse.
3. L’agent peut consulter la liste et la fiche détaillée d’un cimetière.
4. L’agent peut modifier le nom, l’adresse, la capacité et l’état d’un cimetière.
5. Un cimetière déjà référencé par des données métier n’est jamais supprimé physiquement par cette fonctionnalité ; il peut être rendu inactif.
6. Les cimetières inactifs restent consultables et sont visuellement distingués.

### R4 — Contrats backend et Tauri

Le backend doit exposer des contrats déterministes pour lire et modifier la commune et les cimetières.

Critères d’acceptation :

1. Les opérations de lecture, création et modification utilisent des DTO sérialisables et stables.
2. Les erreurs de validation, d’unicité et d’élément introuvable sont différenciées sans exposer une erreur SQLite brute à l’interface.
3. Les opérations sont transactionnelles et leurs tests couvrent succès, validation, doublon et élément introuvable.
4. Les commandes Tauri nécessaires sont enregistrées et appelables depuis le frontend.

### R5 — Parcours interface utilisateur

Le parcours doit être utilisable dans l’application packagée sans commande externe.

Critères d’acceptation :

1. L’agent accède à un écran de paramétrage de la commune et peut enregistrer ses données.
2. Depuis l’écran Cimetières, l’agent voit les données réelles, un état de chargement, un état vide et une erreur récupérable.
3. L’agent peut ouvrir un formulaire de création de cimetière, l’enregistrer et voir immédiatement la nouvelle ligne.
4. L’agent peut ouvrir une fiche, modifier ses champs et constater les nouvelles valeurs sans rechargement externe.
5. Les champs obligatoires et erreurs sont identifiés de façon accessible ; le clavier suffit pour réaliser le parcours.

### R6 — Non-régression et preuves

La fonctionnalité doit démontrer sa compatibilité avec les domaines déjà développés.

Critères d’acceptation :

1. Les tests Rust du backend passent.
2. Les tests TypeScript ciblant hooks, formulaires et pages passent.
3. Un test E2E crée ou configure la commune, crée deux cimetières, modifie l’un d’eux puis vérifie la persistance après réouverture de la vue.
4. Les tests existants des concessions qui utilisent les cimetières restent au vert.
5. Les preuves de revue citent les fichiers modifiés et les sorties exactes des commandes de validation.

## Contraintes techniques

- Rust + Tauri pour le backend desktop ; React + TypeScript pour l’interface ; SQLite pour la persistance.
- Les migrations doivent être additives ou explicitement compatibles avec les données existantes.
- Pas de données simulées dans le parcours principal.
- Pas de dépendance réseau pour le fonctionnement courant.
- Respect des conventions et composants déjà présents dans le dépôt.
- Aucun changement de packaging non requis par cette fonctionnalité.

## Stratégie d’atomisation attendue

Le planificateur doit produire des tâches propriétaires distinctes et ordonnées couvrant au minimum :

1. inventaire ciblé et migration compatible du modèle ;
2. services, validations et tests backend ;
3. commandes Tauri et contrats TypeScript ;
4. UI du référentiel communal ;
5. UI complète des cimetières ;
6. tests E2E et non-régression des concessions.

Chaque critère d’acceptation doit appartenir à une seule tâche. Les dépendances doivent imposer le backend avant les contrats frontend, puis l’UI avant l’E2E.

## Définition de terminé

- tous les critères sont approuvés et rattachés à une tâche propriétaire unique ;
- toutes les tâches sont intégrées ;
- la couverture Autodev atteint 100 % ;
- les suites de tests pertinentes passent ;
- la commune et deux cimetières peuvent être créés, consultés et modifiés dans l’application ;
- les données existantes et le cycle des concessions ne régressent pas.
