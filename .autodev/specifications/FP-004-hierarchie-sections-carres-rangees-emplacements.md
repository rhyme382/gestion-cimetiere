# FEATURE-FP-004 — Hiérarchie sections, carrés, rangées et emplacements

## Contexte

FP-001 a stabilisé le référentiel communal et la gestion de plusieurs cimetières.
La prochaine étape du chemin critique consiste à structurer spatialement les
emplacements avant d'étendre leur CRUD (`FP-005`), leur interface (`FP-006`) et
la cartographie réelle (`FP-037` et `FP-038`).

Le dépôt contient déjà une table `plots`, des modèles Rust, des DTO, un
repository, des commandes Tauri et des contrats TypeScript. Les emplacements
existants sont repérés par des colonnes facultatives `section`, `row` et
`number`. Des concessions référencent déjà `plots.id`.

L'implémentation doit donc normaliser la hiérarchie sans recréer les
emplacements, sans modifier leurs identifiants et sans casser les concessions,
inhumations, PDF, écrans ou tests existants.

## Objectif utilisateur

En tant qu'agent de mairie, je dispose d'une structure spatiale normalisée
cimetière → section → carré → rangée → emplacement, permettant d'identifier
durablement chaque emplacement et de préparer sa gestion administrative et
cartographique.

## Périmètre

- inventaire du modèle `plots` et de ses consommateurs ;
- modèle SQLite normalisé des sections, carrés et rangées ;
- rattachement des emplacements existants à une rangée normalisée ;
- référence administrative stable et unique de chaque emplacement dans son
  cimetière ;
- migration et reprise déterministe des données historiques ;
- modèles et DTO Rust de lecture de la hiérarchie ;
- contrats TypeScript correspondants ;
- repositories nécessaires à la lecture et à la vérification de la hiérarchie ;
- tests de migration, persistance, unicité et non-régression.

## Hors périmètre

- CRUD métier complet des emplacements, capacités et statuts (`FP-005`) ;
- interface de gestion des sections, carrés, rangées et emplacements (`FP-006`) ;
- espaces cinéraires et mémoriels (`FP-007` à `FP-009`) ;
- édition ou rendu cartographique réel (`FP-037` à `FP-042`) ;
- modification du cycle de vie des concessions ;
- suppression physique d'un niveau spatial ;
- import massif, renumérotation globale ou fusion automatique d'emplacements ;
- packaging et dépendances réseau.

## Exigences fonctionnelles

### R1 — Inventaire et compatibilité du modèle existant

L'implémentation doit inventorier les usages actuels de `plots` et préserver les
contrats nécessaires aux fonctionnalités déjà livrées.

Critères d'acceptation :

1. Un inventaire traçable identifie la table `plots`, ses migrations, modèles,
   DTO, repository, commandes Tauri, contrats TypeScript, pages et tests
   consommateurs.
2. Les identifiants existants de `plots` restent inchangés après migration.
3. Les clés étrangères existantes, notamment `concessions.plot_id`, continuent
   de désigner le même emplacement.
4. Les lectures existantes utilisant `cemetery_id`, `section`, `row`, `number`,
   `capacity` et `status` restent compatibles pendant la transition.
5. Aucune donnée historique n'est supprimée ou fusionnée silencieusement.

### R2 — Hiérarchie spatiale normalisée

Le système doit représenter explicitement la hiérarchie suivante :

- un cimetière contient zéro ou plusieurs sections ;
- une section appartient à un seul cimetière ;
- une section contient zéro ou plusieurs carrés ;
- un carré appartient à une seule section ;
- un carré contient zéro ou plusieurs rangées ;
- une rangée appartient à un seul carré ;
- un emplacement appartient à une rangée et conserve son rattachement au
  cimetière.

Chaque section, carré et rangée possède au minimum :

- un identifiant technique stable ;
- un code métier obligatoire ;
- un libellé facultatif ;
- un ordre d'affichage entier positif ou nul ;
- un état actif/inactif ;
- des dates techniques de création et de dernière modification.

Critères d'acceptation :

1. Les sections, carrés et rangées sont persistés dans des tables normalisées
   reliées par des clés étrangères SQLite.
2. Le rattachement d'un enfant à un parent d'un autre cimetière est impossible.
3. Le code métier est nettoyé des espaces périphériques ; sa comparaison
   d'unicité ignore la casse et les espaces répétés.
4. Deux sections d'un même cimetière ne peuvent pas avoir le même code
   normalisé.
5. Deux carrés d'une même section ne peuvent pas avoir le même code normalisé.
6. Deux rangées d'un même carré ne peuvent pas avoir le même code normalisé.
7. Les listes sont ordonnées par ordre d'affichage puis par code normalisé.
8. L'inactivation d'un niveau ne supprime ni ses descendants ni les
   emplacements rattachés.

### R3 — Identité administrative des emplacements

Chaque emplacement doit conserver son identifiant technique et recevoir une
référence administrative stable, lisible et unique dans son cimetière.

Critères d'acceptation :

1. La table `plots` reçoit un rattachement à la rangée normalisée et une
   référence administrative.
2. La référence administrative est obligatoire après migration, nettoyée des
   espaces périphériques et comparée sans tenir compte de la casse.
3. Deux emplacements d'un même cimetière ne peuvent pas avoir la même référence
   administrative normalisée.
4. La même référence peut exister dans deux cimetières différents.
5. La hiérarchie complète d'un emplacement est lisible avec les identifiants,
   codes et libellés de sa section, de son carré et de sa rangée.
6. Les anciennes colonnes `section` et `row` sont conservées pendant cette
   fonctionnalité comme données de compatibilité ; elles ne sont pas supprimées.
7. L'identifiant `plots.id` reste la clé utilisée par les concessions et les
   autres domaines existants.

### R4 — Migration déterministe des données historiques

La migration doit rattacher tous les emplacements existants à la nouvelle
hiérarchie sans perte de données.

Règles de reprise :

- une ancienne valeur `section` non vide crée ou réutilise une section de même
  code normalisé dans le cimetière ;
- une section absente ou vide utilise une section technique `NON-CLASSE` ;
- faute d'ancien niveau carré, un carré technique `GENERAL` est créé sous
  chaque section concernée ;
- une ancienne valeur `row` crée ou réutilise une rangée dont le code est sa
  représentation décimale ;
- une rangée absente utilise le code technique `NON-CLASSEE` ;
- la référence historique d'un emplacement est initialisée de façon
  déterministe à `EMP-{id}` afin de garantir l'unicité sans modifier les
  coordonnées historiques ;
- les valeurs originales `section`, `row` et `number` restent inchangées.

Critères d'acceptation :

1. Une base vide reçoit le nouveau schéma sans erreur.
2. Une base contenant des emplacements avec section et rangée est migrée vers
   la hiérarchie correspondante.
3. Une base contenant des coordonnées partielles ou nulles est migrée via les
   niveaux techniques prévus.
4. Plusieurs emplacements partageant une ancienne section et une ancienne
   rangée réutilisent les mêmes niveaux normalisés.
5. La migration conserve exactement le nombre et les identifiants des
   emplacements, concessions et inhumations existants.
6. Chaque emplacement migré possède une référence administrative unique et un
   rattachement hiérarchique exploitable.
7. La migration est transactionnelle et idempotente.
8. Une erreur de migration provoque un rollback complet, sans état partiel.

### R5 — Modèles, repositories et contrats partagés

Le backend et le frontend doivent disposer de contrats déterministes pour lire
la hiérarchie, sans anticiper le CRUD complet de FP-005.

Critères d'acceptation :

1. Des modèles et DTO sérialisables représentent une section, un carré, une
   rangée et le chemin spatial complet d'un emplacement.
2. `PlotDTO` expose la référence administrative et les informations
   hiérarchiques nécessaires sans retirer ses champs historiques.
3. Les repositories permettent de relire les niveaux d'un cimetière et le
   chemin complet d'un emplacement.
4. Une demande portant sur un cimetière, une section, un carré, une rangée ou un
   emplacement inexistant produit une erreur `NotFound` différenciée.
5. Les contrats TypeScript correspondent aux DTO Rust et restent compatibles
   avec les consommateurs actuels de `PlotDTO`.
6. Cette fonctionnalité n'ajoute pas les commandes de création, modification
   ou suppression des niveaux spatiaux ; elles appartiennent à FP-005.
7. Aucune erreur SQLite brute n'est exposée comme contrat applicatif.

### R6 — Non-régression et preuves

La fonctionnalité doit démontrer la préservation du noyau existant.

Critères d'acceptation :

1. Les tests Rust du backend passent.
2. Les tests de migration couvrent une base vide, une base historique complète,
   des coordonnées partielles, les niveaux techniques et l'idempotence.
3. Les tests d'intégration vérifient la persistance et la lecture du chemin
   cimetière → section → carré → rangée → emplacement après réouverture.
4. Les tests démontrent l'unicité normalisée des codes à chaque niveau et de la
   référence d'emplacement dans un cimetière.
5. Les tests existants de concessions, inhumations, PDF et emplacements restent
   au vert avec les mêmes `plot_id`.
6. Les tests TypeScript des bindings et des consommateurs de `PlotDTO` passent.
7. Le rapport de fin de tâche cite les fichiers réellement modifiés, les
   commandes exécutées, leurs codes de sortie et leurs résultats stables.

## Contraintes techniques

- Rust + Tauri pour le backend, SQLite pour la persistance et TypeScript pour
  les contrats frontend.
- Les migrations doivent être additives ou explicitement compatibles.
- Ne pas modifier `001_initial_schema.sql` pour une base déjà déployée ; ajouter
  une nouvelle migration versionnée.
- Activer et vérifier les clés étrangères SQLite.
- Conserver les identifiants de `plots`.
- Ne pas introduire de dépendance réseau ou de bibliothèque SIG.
- Ne pas ajouter d'interface utilisateur ou de données simulées.
- Ne pas modifier le packaging.
- Les niveaux techniques de reprise doivent être documentés et distinguables
  des niveaux saisis ultérieurement par un agent.
- Toute modification d'une dépendance doit être explicitement autorisée et
  justifiée dans le backlog.

## Stratégie d'atomisation attendue

Le planificateur doit produire des tâches propriétaires distinctes et ordonnées
couvrant au minimum :

1. inventaire ciblé, nouvelle migration et reprise compatible des données ;
2. modèles Rust, DTO et règles du domaine hiérarchique ;
3. repositories de lecture, chemin spatial et tests d'intégration ;
4. contrats TypeScript et non-régression des consommateurs de `PlotDTO` ;
5. preuve finale de migration, persistance et non-régression.

Chaque critère d'acceptation doit appartenir à une seule tâche. Les dépendances
doivent imposer la migration avant les modèles et repositories, puis les
contrats partagés avant la preuve finale.

Aucune tâche de FP-004 ne doit implémenter le CRUD complet de FP-005 ni
l'interface de FP-006.

## Définition de terminé

- tous les critères sont rattachés à une tâche propriétaire unique et approuvés ;
- toutes les tâches sont intégrées ;
- la couverture Autodev atteint 100 % ;
- les migrations sont transactionnelles, idempotentes et compatibles avec les
  bases existantes ;
- tous les emplacements existants conservent leur identifiant et leurs
  références depuis les concessions ;
- chaque emplacement possède une référence administrative unique et un chemin
  hiérarchique relisible ;
- les suites Rust et TypeScript pertinentes passent ;
- FP-005 peut implémenter le CRUD des niveaux et emplacements sans nouvelle
  refonte du schéma.
