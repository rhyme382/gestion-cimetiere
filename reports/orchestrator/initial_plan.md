# Plan initial d'orchestration

Date : 2026-06-15

## Objectif

Structurer le projet avant implémentation lourde afin de permettre à plusieurs agents de travailler de manière autonome sur un socle commun.

## Décisions de cadrage

- Application desktop locale basée sur Tauri.
- Frontend en React + TypeScript.
- Backend local avec SQLite embarqué.
- Packaging cible : NSIS sous Windows, AppImage puis `.deb` sous Linux.
- Qualité : Vitest pour l'unitaire et l'intégration, Playwright pour l'end-to-end.

## Lots initiaux

1. Cadrage et architecture
   - finaliser roadmap, prompts et suivi des agents ;
   - confirmer l'organisation des tâches atomiques.
2. Socle technique
   - initialiser l'application Tauri ;
   - poser l'outillage TypeScript, lint, tests et CI locale.
3. Domaine métier central
   - modéliser concessions, emplacements, défunts, ayants droit et documents ;
   - créer schéma SQLite et migrations.
4. Interface métier prioritaire
   - tableau de bord ;
   - listes et fiches ;
   - recherche globale ;
   - alertes d'échéance.
5. Cartographie
   - modèle de plan ;
   - rendu interactif ;
   - synchronisation avec les emplacements.
6. Packaging et recette
   - builds reproductibles ;
   - installation Windows/Linux ;
   - campagne de validation.

## Répartition proposée

- Agent frontend : shell applicatif, pages métier, composants réutilisables.
- Agent backend : modèle de données, services métier, commandes Tauri.
- Agent mapping : plan du cimetière, interactions, synchronisation des états.
- Agent packaging : builds, installeurs, documentation d'installation.
- Agent QA : stratégie de tests, jeux de données, non-régression.

## Principes de coordination

- Travailler par tâches courtes et atomiques.
- Documenter toute décision structurante dans `agents/reports/`.
- Ne pas supprimer de code sans justification explicite.
- Valider par tests tout changement de comportement.

## Risques initiaux

- Complexité métier des concessions et des états administratifs.
- Risque de divergence entre cartographie et données métier.
- Risque de surcharge UX si l'interface n'est pas disciplinée.
- Variabilité du packaging desktop selon l'OS cible.

## Prochaine étape

Passer de l'orchestration initiale à la mise en place du socle technique et à la création de la première tranche de tâches d'implémentation.
