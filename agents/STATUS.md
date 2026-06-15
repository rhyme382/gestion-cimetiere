# Statut des agents

Date de référence : 2026-06-15

## Vue d'ensemble

| Agent | Domaine | Statut | Livrable attendu | Dépendances |
| --- | --- | --- | --- | --- |
| orchestrator | Pilotage | En cours | Roadmap, file de tâches, prompts, suivi global | SPEC.md |
| frontend | Interface React/Tauri | À lancer | Shell applicatif, design system, vues métier | roadmap, prompt frontend |
| backend | Modèle métier et persistance | À lancer | Schéma SQLite, services Tauri, règles métier | roadmap, prompt backend |
| mapping | Cartographie cimetière | À lancer | Moteur de plan, couches, interactions SIG légères | roadmap, prompt mapping |
| packaging | Distribution poste mairie | À lancer | Builds Windows/Linux, installeurs, documentation d'installation | roadmap, prompt packaging |
| qa | Validation et tests | À lancer | Stratégie de tests, suites Vitest/Playwright, recette | roadmap, prompt QA |

## Décisions actées

- Stack cible : Tauri + React + TypeScript.
- Stockage local prioritaire : SQLite embarqué.
- Plateformes cibles : Windows et Linux.
- Packaging prioritaire : NSIS pour Windows, AppImage puis `.deb` pour Linux.
- Tests cibles : Vitest pour l'unitaire/intégration, Playwright pour l'end-to-end.

## Blocages connus

- Aucun blocage fonctionnel identifié à ce stade.
- Création de branche Git impossible dans cette sandbox car les écritures dans `.git/refs` sont en lecture seule.

## Prochaine mise à jour attendue

- Après création des prompts spécialisés.
- Après découpage des premières tâches atomiques d'implémentation.
