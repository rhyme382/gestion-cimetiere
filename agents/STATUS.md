# Statut des agents

Date de référence : 2026-06-15

## Vue d'ensemble

| Agent | Domaine | Statut | Livrable attendu | Dépendances |
| --- | --- | --- | --- | --- |
| orchestrator | Pilotage | En cours | Roadmap MVP, backlog atomique, dépendances, suivi global | SPEC.md |
| frontend | Interface React/Tauri | 🚀 En cours (MVP-02, MVP-06) | Shell ✅, composants UI ✅, vues métier (MVP-12+) | MVP-01 ✅, MVP-05A ✅ |
| backend | Modèle métier et persistance | Prêt à lancer | Structure workspace, schéma SQLite, contrats Tauri | aucune |
| mapping | Cartographie cimetière | 🚀 En cours (MVP-07) | Format de plan MVP ✅, rendu simple (MVP-14), sélection d’emplacement (MVP-14) | MVP-04 ✅, MVP-07 ✅ |
| packaging | Distribution poste mairie | **En cours (MVP-08)** | Config Tauri NSIS/AppImage/.deb, scripts build, guide install | MVP-01, MVP-02 |
| qa | Validation et tests | **MVP-03 livré** | Stratégie de tests ✅, conventions QA ✅ ; livraison de cadrage uniquement, sans implémentation complète des tests | MVP-01 ✅ |

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

## Avancement projet

| Phase | Statut | Avancement |
| --- | --- | --- |
| Phase 0 — Pilotage et socle | ✅ Terminé | 100% |
| Phase 1 — Noyau métier MVP | 🚀 En cours | 15% (socle créé, stub impl.) |
| Phase 2 — Interface métier MVP | 🚀 En cours (MVP-02, MVP-06) | 25% (shell + design system en place) |
| Phase 3 — Cartographie MVP | 🚀 En cours | 50% (MVP-07 ✅, MVP-14 en attente) |
| Phase 4 — Documents, alertes, sauvegarde | Dépend de Phase 2 | 0% |
| Phase 5 — Packaging et validation | Dépend de Phase 4 | 0% |

## Checklist de lancement

- [x] Dépôt nettoyé et repositionné
- [x] Infrastructure d'orchestration initialisée
- [x] Prompts spécialisés pour tous les agents
- [x] SPEC.md complète et validée
- [x] ROADMAP.md avec backlog priorisé
- [x] `agents/STATUS.md` défini comme suivi officiel
- [x] Rapports MVP-00, MVP-01, MVP-02, MVP-03, MVP-04, MVP-05, MVP-05A, MVP-06
- [x] Exécution MVP-00 — ✅ Socle Rust/Tauri
- [x] Exécution MVP-01 — ✅ Architecture applicative (modules, layering)
- [x] Exécution MVP-04 — ✅ Schéma SQLite + migrations compilables
- [x] Exécution MVP-05 — ✅ DTOs Tauri + commandes stubs
- [x] Exécution MVP-05A — ✅ Types TypeScript préparés (specta::Type)
- [x] Exécution MVP-02 — ✅ Shell Tauri + React + TypeScript (router, layout, Tailwind)
- [x] Exécution MVP-06 — ✅ Composants UI + pages stubs + types mirroir Rust
- [x] Exécution MVP-07 — ✅ Format cartographique MVP stabilisé

## Blocages connus

- Aucun blocage fonctionnel identifié à ce stade.
- Aucun prompt spécialisé manquant identifié.
- **MAPPING DÉBLOQUÉ** : MVP-07 (format cartographique) stabilisé ; MVP-14 (rendu) peut démarrer après MVP-02 ✅ et contrats Tauri stubs.
- Le lancement parallèle doit respecter les dépendances d’entrée suivantes :
  - `backend` démarre immédiatement sur MVP-00 et MVP-01 ;
  - `qa` démarre dès que MVP-01 est cadré ;
  - `frontend` attend la stabilisation de MVP-01 puis MVP-05A pour les vues métier ;
  - `mapping` peut démarrer sur MVP-14 dès que MVP-07 ✅ + MVP-02 ✅ en place ;
  - `packaging` peut cadrer sa stratégie après MVP-01 et lancer les builds sur squelette après MVP-02.

## Prochain lancement recommandé

1. Lancer `backend` sur MVP-00 puis MVP-01.
2. Lancer `packaging` sur MVP-08 dès que MVP-01 est stabilisé.
3. ~~Lancer `qa` sur MVP-03~~ **✅ MVP-03 livré** → stratégie QA en place, prêt pour Phase 1 (MVP-24, MVP-25, MVP-26, MVP-27).
4. Lancer `frontend` sur MVP-02 une fois MVP-01 validé.
5. Lancer `mapping` sur MVP-07 une fois MVP-04 cadré.

## Indicateur de readiness

- Projet prêt pour lancer `backend` : oui.
- Projet prêt pour lancer `frontend` : **MVP-02 + MVP-06 TERMINÉ ✅**, prêt pour MVP-12 (vues métier).
- Projet prêt pour lancer `mapping` : **oui, MVP-07 ✅ stabilisé**, en attente de MVP-02 et commandes Tauri stubs pour MVP-14.
- Projet prêt pour lancer `packaging` : oui, après sortie de MVP-01 ✅ puis MVP-02.
- Projet prêt pour lancer `qa` Phase 1 (MVP-24, MVP-25, MVP-26) : oui, MVP-03 stratégie livrée sans exécution complète de tests, backend MVP-04+ en cours.
