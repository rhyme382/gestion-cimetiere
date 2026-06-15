# MVP-03 — Définir la stratégie de tests du MVP

**Date :** 2026-06-15  
**Agent :** qa  
**Statut :** Livré — stratégie QA définie, sans implémentation complète des tests  
**Dépend de :** MVP-01

## Objectif

Définir la stratégie de validation du MVP, les conventions QA, les niveaux de tests, les jeux de données de référence et les critères de blocage, sans développer ni exécuter l’ensemble des tests métier.

## Fichiers modifiés

- `orchestration/qa_strategy.md`
- `orchestration/qa_conventions.md`

## Décisions prises

- Structurer la validation en quatre niveaux :
  - tests unitaires ;
  - tests d’intégration ;
  - tests end-to-end ;
  - validation manuelle ciblée.
- Retenir `Vitest` pour les tests unitaires et d’intégration côté frontend, et `Playwright` pour les flux E2E.
- Formaliser une nomenclature commune pour les fichiers de test et les identifiants de cas (`T-<domaine>-<numéro>`).
- Définir un socle de fixtures MVP reproductibles pour les scénarios critiques.
- Poser des critères de couverture, de non-régression et de blocage par phase.

## Problèmes connus

- `MVP-03` couvre une stratégie QA et des conventions, pas l’implémentation complète des suites de test.
- Les tests automatisés décrits dans la stratégie n’ont pas encore tous été écrits.
- Aucun rapport d’exécution de tests métier n’est disponible à ce stade.

## Résultats des tests

- Aucun test métier exécuté dans le cadre de `MVP-03`.
- Livraison limitée au cadrage QA, à la documentation des conventions et à la préparation du travail des phases suivantes.

## Prochaine étape

1. Utiliser cette stratégie pour lancer les suites QA des phases suivantes :
   - `MVP-24` ;
   - `MVP-25` ;
   - `MVP-26` ;
   - `MVP-27`.
2. Aligner les futures implémentations backend, frontend, mapping et packaging sur les conventions définies.
3. Commencer l’implémentation des fixtures et des premières suites une fois les lots backend stabilisés.
