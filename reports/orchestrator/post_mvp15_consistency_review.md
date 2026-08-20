# Revue de cohérence post-MVP-15

Date : 2026-06-16
Agent : orchestrator
Statut : ✅ Alignement documentaire effectué

## Objectif

Réaligner la documentation de pilotage après MVP-15 pour que `agents/STATUS.md` et `reports/dev/MVP-15.md` soient cohérents avec les sources de vérité officielles :

1. `ROADMAP.md`
2. `agents/QUEUE.md`
3. `agents/STATUS.md`

## Fichiers modifiés

- `agents/STATUS.md`
- `reports/dev/MVP-15.md`
- `reports/orchestrator/post_mvp15_consistency_review.md`

## Incohérences constatées

- `agents/STATUS.md` déclarait MVP-15 livré dans la checklist, mais conservait encore MVP-15 comme “prochain lancement”.
- `agents/STATUS.md` gardait un indicateur de readiness frontend obsolète, encore positionné sur MVP-12.
- `reports/dev/MVP-15.md` associait à tort la suite immédiate de MVP-17 à des évolutions cartographiques, alors que la roadmap officielle définit :
  - `MVP-16` = backend alertes d’échéance
  - `MVP-17` = frontend centre d’alertes minimal

## Décisions prises

- Considérer `ROADMAP.md` et `agents/QUEUE.md` comme références prioritaires pour la séquence MVP suivante.
- Marquer explicitement `MVP-16` comme prochain lot à lancer dans `agents/STATUS.md`.
- Mettre le readiness frontend en cohérence avec l’état réel : `MVP-15` terminé, `MVP-17` dépendant de `MVP-16`.
- Reclasser les améliorations cartographiques mentionnées dans `reports/dev/MVP-15.md` en travaux post-MVP ou post-séquence immédiate, et non en `MVP-17`.

## Validation

- Aucun code applicatif modifié.
- Aucun fichier backend modifié.
- Alignement vérifié avec `ROADMAP.md` et `agents/QUEUE.md`.

## Prochaine étape

Lancer `backend` sur `MVP-16` pour implémenter les alertes d’échéance MVP, puis enchaîner `frontend` sur `MVP-17` pour intégrer le centre d’alertes minimal.
