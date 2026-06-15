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

## Résumé exécutif

Le projet a produit plusieurs rapports de cadrage utiles, mais les lots critiques attendus pour le lancement de `frontend` et `mapping` ne sont pas encore stabilisés au sens opérationnel.

Constats majeurs :
- `MVP-00`, `MVP-01`, `MVP-04`, `MVP-05` et `MVP-05A` sont tous encore marqués `En cours de définition`.
- Les rapports décrivent des intentions, structures proposées et prochaines étapes, mais pas une stabilisation effective, ni une implémentation validée, ni des tests exécutés.
- `MVP-07` n’a pas été fourni dans les éléments audités et aucun rapport `reports/dev/MVP-07.md` n’est disponible ici.
- `MVP-08` a démarré comme stratégie packaging, mais reste incomplet.

## Audit frontend

### Pré requis attendus

Selon `ROADMAP.md`, `agents/QUEUE.md` et `agents/STATUS.md`, le lancement utile de `frontend` dépend de :
- `MVP-01` ;
- `MVP-05A` ;
- et, pour les vues métier, d’un socle backend réellement stabilisé.

### Vérification des lots backend nécessaires

#### MVP-00 — Structure du dépôt et conventions

Verdict : insuffisant pour déclarer stable.

Motifs :
- statut du rapport : `En cours de définition` ;
- tâches clés non cochées ;
- aucun résultat de test ;
- aucune preuve d’exécution ou de validation finale de l’arborescence.

#### MVP-01 — Architecture applicative desktop

Verdict : insuffisant pour déclarer stable.

Motifs :
- statut du rapport : `En cours de définition` ;
- architecture proposée mais non validée comme standard effectif du dépôt ;
- compatibilité frontend évoquée, mais pas démontrée ;
- aucun test ni validation de structure réellement achevés.

#### MVP-04 — Schéma SQLite et entités cœur

Verdict : insuffisant pour déclarer stable.

Motifs :
- statut du rapport : `En cours de définition` ;
- schéma proposé seulement en aperçu ;
- migrations non livrées ;
- plusieurs décisions restent ouvertes ;
- aucun test de migration ou de cohérence exécuté.

#### MVP-05 — Contrats API/Tauri et DTO partagés

Verdict : insuffisant pour déclarer stable.

Motifs :
- statut du rapport : `En cours de définition` ;
- structures et commandes proposées, mais pas stabilisées ;
- stratégie d’erreur, versioning et validation encore à arbitrer ;
- aucun contrat testé.

#### MVP-05A — Génération automatique des types TypeScript

Verdict : insuffisant pour déclarer stable.

Motifs :
- statut du rapport : `En cours de définition` ;
- outil recommandé (`specta`) mais pas acté par une implémentation confirmée ;
- flux de génération décrit mais pas intégré ;
- aucune génération réellement vérifiée ;
- aucun test ni preuve de non-divergence Rust ↔ TypeScript.

### Conclusion frontend

Le frontend ne doit pas être lancé au-delà d’un éventuel cadrage théorique.

Raisons bloquantes :
- absence de stabilisation réelle de `MVP-01` ;
- absence de DTO versionnés effectivement figés ;
- absence de génération TypeScript effectivement en place et validée ;
- absence de résultats de tests sur les contrats et la structure.

Verdict explicite :

`FRONTEND_BLOCKED`

## Audit mapping

### Pré requis attendus

Selon le backlog :
- `MVP-07` dépend de `MVP-04` ;
- `MVP-14` dépend de `MVP-07` et `MVP-10`.

### Vérification des éléments disponibles

#### MVP-04 — Modèle de données emplacements

Verdict : insuffisant pour lancer utilement mapping.

Motifs :
- schéma seulement proposé ;
- structure des emplacements non stabilisée ;
- questions ouvertes sur types, états, historisation et indexation.

#### MVP-07 — Format cartographique MVP

Verdict : absent dans les artefacts audités.

Motifs :
- aucun rapport `reports/dev/MVP-07.md` fourni ;
- aucune spécification formelle du format cartographique MVP lue ;
- aucun contrat entre données `plots` et rendu cartographique n’est stabilisé.

### Conclusion mapping

Le mapping ne peut pas être lancé proprement.

Raisons bloquantes :
- `MVP-04` n’est pas stabilisé ;
- `MVP-07` est manquant dans les éléments audités ;
- le couplage futur avec `MVP-10` n’est pas encore matérialisé.

Verdict explicite :

`MAPPING_BLOCKED`

## Audit packaging

### MVP-08 — Stratégie packaging Windows/Linux

Verdict : utile comme cadrage, mais encore incomplet.

Motifs :
- statut du rapport : `Initié` ;
- dépendances du rapport lui-même : `MVP-01 stabilisé` et `MVP-02 terminé`, ce qui n’est pas encore démontré ici ;
- configuration Tauri non stabilisée ;
- scripts NSIS/AppImage non implémentés ;
- aucun test d’artefact exécuté ;
- aucune validation sur machine réelle.

Conclusion :
- `MVP-08` constitue une base de stratégie acceptable ;
- `MVP-08` n’est pas suffisant pour considérer le packaging prêt ou sécurisé.

## Recommandations immédiates

1. Faire passer `MVP-00`, `MVP-01`, `MVP-04`, `MVP-05` et `MVP-05A` du statut “définition” à un statut stabilisé avec preuves concrètes.
2. Exiger un rapport `MVP-07` avant tout lancement de `mapping`.
3. Ne lancer `frontend` que lorsque les DTO, conventions de sérialisation et génération TypeScript sont réellement figés.
4. Considérer `MVP-08` comme un cadrage de packaging, pas comme un lot prêt à validation finale.

## Verdict final

- FRONTEND : `FRONTEND_BLOCKED`
- MAPPING : `MAPPING_BLOCKED`
