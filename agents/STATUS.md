# Statut des agents

Date de référence : 2026-06-15

## Vue d'ensemble

| Agent | Domaine | Statut | Livrable attendu | Dépendances |
| --- | --- | --- | --- | --- |
| orchestrator | Pilotage | En cours | Roadmap MVP, backlog atomique, dépendances, suivi global | SPEC.md |
| frontend | Interface React/Tauri | Prêt à lancer | Shell applicatif, composants UI, vues MVP | MVP-01, MVP-05A |
| backend | Modèle métier et persistance | Prêt à lancer | Structure workspace, schéma SQLite, contrats Tauri | aucune |
| mapping | Cartographie cimetière | Prêt à lancer sous dépendance | Format de plan MVP, rendu simple, sélection d’emplacement | MVP-04 |
| packaging | Distribution poste mairie | Prêt à lancer sous dépendance | Stratégie packaging, builds Windows/Linux | MVP-01 puis MVP-02 |
| qa | Validation et tests | Prêt à lancer | Stratégie de tests, fixtures, suites de validation | MVP-01 |

## Décisions actées

- Stack cible : Tauri + React + TypeScript.
- Stockage local prioritaire : SQLite embarqué.
- Plateformes cibles : Windows et Linux.
- Packaging prioritaire : NSIS pour Windows, AppImage puis `.deb` pour Linux.
- Tests cibles : Vitest pour l'unitaire/intégration, Playwright pour l'end-to-end.
- Backend local recommandé : Rust via commandes Tauri.
- Cartographie MVP : format simple et moteur léger compatible Tauri.
- MVP strict : noyau métier, recherche simple, cartographie simple, PDF simple, sauvegarde/restauration, packaging.
- Contrats d’échange MVP : DTO Rust/TypeScript partagés, versionnés, avec génération automatique des types frontend.
- Chaque tâche MVP terminée doit produire un rapport `reports/dev/MVP-XX.md` avec objectif, fichiers modifiés, décisions prises, problèmes connus, résultats des tests et prochaine étape.

## Blocages connus

- Aucun blocage fonctionnel identifié à ce stade.
- Aucun prompt spécialisé manquant identifié.
- Le lancement parallèle doit respecter les dépendances d’entrée suivantes :
  - `backend` démarre immédiatement sur MVP-00 et MVP-01 ;
  - `qa` démarre dès que MVP-01 est cadré ;
  - `frontend` attend la stabilisation de MVP-01 puis MVP-05A pour les vues métier ;
  - `mapping` attend la stabilisation du modèle emplacement issu de MVP-04 ;
  - `packaging` peut cadrer sa stratégie après MVP-01 et lancer les builds sur squelette après MVP-02.

## Prochain lancement recommandé

1. Lancer `backend` sur MVP-00 puis MVP-01.
2. Lancer `packaging` sur MVP-08 dès que MVP-01 est stabilisé.
3. Lancer `qa` sur MVP-03 dès que MVP-01 est stabilisé.
4. Lancer `frontend` sur MVP-02 une fois MVP-01 validé.
5. Lancer `mapping` sur MVP-07 une fois MVP-04 cadré.

## Indicateur de readiness

- Projet prêt pour lancer `backend` : oui.
- Projet prêt pour lancer `frontend` : oui, après sortie de MVP-01.
- Projet prêt pour lancer `mapping` : oui, après sortie de MVP-04.
- Projet prêt pour lancer `packaging` : oui, après sortie de MVP-01 puis MVP-02.
- Projet prêt pour lancer `qa` : oui, après sortie de MVP-01.
