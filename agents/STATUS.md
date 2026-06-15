# Statut des agents

Date de référence : 2026-06-15

## Vue d'ensemble

| Agent | Domaine | Statut | Livrable attendu | Dépendances |
| --- | --- | --- | --- | --- |
| orchestrator | Pilotage | En cours | Roadmap MVP, backlog atomique, dépendances, suivi global | SPEC.md |
| frontend | Interface React/Tauri | 🚀 En cours (API prep) | Shell ✅, composants UI ✅, intégration API ✅, vues métier (MVP-12+) | MVP-01 ✅, MVP-05A ✅, Backend commands en attente |
| backend | Modèle métier et persistance | 🚀 En cours (MVP-10, MVP-11) | Commandes Tauri CRUD (cimeteries, plots, concessions, individuals, burials) | MVP-05 ✅, MVP-09 (migrations) ✅ |
| mapping | Cartographie cimetière | ✅ Phase 3 terminée | Format de plan MVP ✅, rendu simple ✅, sélection d’emplacement ✅ | MVP-04 ✅, MVP-07 ✅, MVP-14 ✅ |
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
| Phase 1 — Noyau métier MVP | 🚀 En cours | 50% (repositories et commandes Tauri MVP-10/11 en implémentation) |
| Phase 2 — Interface métier MVP | 🚀 En cours (MVP-02, MVP-06) | 25% (shell + design system en place) |
| Phase 3 — Cartographie MVP | ✅ Terminé | 100% (MVP-07 ✅, MVP-14 ✅) |
| Phase 4 — Documents, alertes, sauvegarde | Dépend de Phase 2 | 0% |
| Phase 5 — Packaging et validation | Dépend de Phase 4 | 0% |

## Checklist de lancement

- [x] Dépôt nettoyé et repositionné
- [x] Infrastructure d'orchestration initialisée
- [x] Prompts spécialisés pour tous les agents
- [x] SPEC.md complète et validée
- [x] ROADMAP.md avec backlog priorisé
- [x] `agents/STATUS.md` défini comme suivi officiel
- [x] Rapports MVP-00, MVP-01, MVP-02, MVP-03, MVP-04, MVP-05, MVP-05A, MVP-06, MVP-07, MVP-14
- [x] Exécution MVP-00 — ✅ Socle Rust/Tauri
- [x] Exécution MVP-01 — ✅ Architecture applicative (modules, layering)
- [x] Exécution MVP-04 — ✅ Schéma SQLite + migrations compilables
- [x] Exécution MVP-05 — ✅ DTOs Tauri + commandes stubs
- [x] Exécution MVP-05A — ✅ Types TypeScript préparés (specta::Type)
- [x] Exécution MVP-02 — ✅ Shell Tauri + React + TypeScript (router, layout, Tailwind)
- [x] Exécution MVP-06 — ✅ Composants UI + pages stubs + types mirroir Rust
- [x] Exécution MVP-07 — ✅ Format cartographique MVP stabilisé
- [x] Exécution MVP-14 — ✅ Rendu cartographique SVG + sélection (mock data, tests ✅)
- [ ] Exécution MVP-10 — 🚀 En cours, Commandes Tauri cemeteries + plots
- [ ] Exécution MVP-11 — 🚀 En cours, Commandes Tauri concessions + individuals + burials
- [ ] Rapports MVP-10, MVP-11 — À générer après implémentation

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

1. ~~Lancer `backend` sur MVP-00 puis MVP-01~~ **✅ MVP-00 à MVP-07 TERMINÉ**
2. **🚀 EN COURS : `backend` sur MVP-10 et MVP-11** — Commandes Tauri pour cimeteries, plots, concessions, individuals, burials (plan: `docs/superpowers/plans/2026-06-15-MVP-10-11-tauri-commands.md`)
3. ~~Lancer `packaging` sur MVP-08~~ **🚀 EN COURS**
4. ~~Lancer `qa` sur MVP-03~~ **✅ MVP-03 livré** → stratégie QA en place, prêt pour Phase 1 (MVP-24, MVP-25, MVP-26, MVP-27).
5. Lancer `frontend` sur MVP-12 (dashboard, listes concessions) dès que MVP-10/11 livrés.
6. ~~Lancer `mapping` sur MVP-14~~ **✅ MVP-14 TERMINÉ** → Rendu + sélection ✅, swap mock data avec API Tauri real quand MVP-10/11 livré.

## Indicateur de readiness

- Projet prêt pour lancer `backend` : oui.
- Projet prêt pour lancer `frontend` : **MVP-02 + MVP-06 TERMINÉ ✅**, prêt pour MVP-12 (vues métier).
- Projet prêt pour lancer `mapping` : **✅ MVP-14 TERMINÉ**, composant rendu SVG + sélection implémentés avec 25 tests passants ; intégration réelle dépend de MVP-10/11.
- Projet prêt pour lancer `packaging` : oui, après sortie de MVP-01 ✅ puis MVP-02.
- Projet prêt pour lancer `qa` Phase 1 (MVP-24, MVP-25, MVP-26) : oui, MVP-03 stratégie livrée sans exécution complète de tests, backend MVP-04+ en cours.
