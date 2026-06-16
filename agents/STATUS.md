# Statut des agents

Date de référence : 2026-06-16

## Vue d'ensemble

| Agent | Domaine | Statut | Livrable attendu | Dépendances |
| --- | --- | --- | --- | --- |
| orchestrator | Pilotage | En cours | Roadmap MVP, backlog atomique, dépendances, suivi global | SPEC.md |
| frontend | Interface React/Tauri | ✅ MVP-12/13/15/17/19 livré | Shell ✅, UI ✅, API ✅, dashboard ✅, listes ✅, fiches ✅, recherche ✅, cartographie ✅, alertes ✅, PDF export ✅ | MVP-01 ✅, MVP-05A ✅, MVP-10 ✅, MVP-11 ✅, MVP-14 ✅, MVP-16 ✅, MVP-18 ✅ |
| backend | Modèle métier et persistance | ✅ MVP-10/11/16/18 livré (correction PDF) | Commandes Tauri CRUD ✅, alertes d'échéance ✅, PDF administratif binaire réel ✅, vues métier complètes ✅ | MVP-05 ✅, MVP-09 (migrations) ✅ |
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
| Phase 1 — Noyau métier MVP | ✅ Terminé | 100% (repositories ✅, commandes Tauri ✅, alertes ✅) |
| Phase 2 — Interface métier MVP | ✅ Terminée | 100% (shell + design system + écrans métier) |
| Phase 3 — Cartographie MVP | ✅ Terminé | 100% (MVP-07 ✅, MVP-14 ✅) |
| Phase 4 — Documents, alertes, sauvegarde | ✅ Partiellement avancé | 66% (alertes ✅, PDF ✅) |
| Phase 5 — Packaging et validation | Dépend de Phase 4 | 0% |

## Checklist de lancement

- [x] Dépôt nettoyé et repositionné
- [x] Infrastructure d'orchestration initialisée
- [x] Prompts spécialisés pour tous les agents
- [x] SPEC.md complète et validée
- [x] ROADMAP.md avec backlog priorisé
- [x] `agents/STATUS.md` défini comme suivi officiel
- [x] Rapports MVP-00, MVP-01, MVP-02, MVP-03, MVP-04, MVP-05, MVP-05A, MVP-06, MVP-07, MVP-10, MVP-11, MVP-12, MVP-13, MVP-14, MVP-15, MVP-16, MVP-17, MVP-18, MVP-19
- [x] Exécution MVP-00 — ✅ Socle Rust/Tauri
- [x] Exécution MVP-01 — ✅ Architecture applicative (modules, layering)
- [x] Exécution MVP-04 — ✅ Schéma SQLite + migrations compilables
- [x] Exécution MVP-05 — ✅ DTOs Tauri + commandes stubs
- [x] Exécution MVP-05A — ✅ Types TypeScript préparés (specta::Type)
- [x] Exécution MVP-02 — ✅ Shell Tauri + React + TypeScript (router, layout, Tailwind)
- [x] Exécution MVP-06 — ✅ Composants UI + pages stubs + types mirroir Rust
- [x] Exécution MVP-07 — ✅ Format cartographique MVP stabilisé
- [x] Exécution MVP-02 — ✅ Shell Tauri + React + TypeScript
- [x] Exécution MVP-06 — ✅ Design system + composants UI + types
- [x] Exécution Frontend API prep — ✅ Hooks + services + états loading/error
- [x] Exécution MVP-10 — ✅ Commandes Tauri cemeteries + plots
- [x] Exécution MVP-11 — ✅ Commandes Tauri concessions + individuals + burials
- [x] Exécution MVP-12 — ✅ Dashboard, liste concessions, fiche concession
- [x] Exécution MVP-13 — ✅ Liste défunts, fiche défunt, recherche globale
- [x] Exécution MVP-14 — ✅ Rendu cartographique SVG + sélection
- [x] Exécution MVP-15 — ✅ Intégration cartographie ↔ fiches métier
- [x] Exécution MVP-16 — ✅ Alertes d’échéance backend
- [x] Exécution MVP-17 — ✅ Centre d’alertes (widget + tableau + acquittement)
- [x] Exécution MVP-18 — ✅ Génération PDF administratif simple
- [x] Exécution MVP-19 — ✅ Intégration interface génération PDF (bouton, loading, success/error states)

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

1. ~~Lancer `backend` sur MVP-00 puis MVP-01~~ **✅ MVP-00 à MVP-11 TERMINÉ**
2. **✅ LIVRÉ : `backend` sur MVP-10 et MVP-11** — Commandes Tauri pour cemeteries, plots, concessions, individuals, burials (21 handlers, 27+ unit tests)
3. ~~Lancer `packaging` sur MVP-08~~ **🚀 EN COURS**
4. ~~Lancer `qa` sur MVP-03~~ **✅ MVP-03 livré** → stratégie QA en place, prêt pour Phase 1 (MVP-24, MVP-25, MVP-26, MVP-27).
5. **✅ LIVRÉ : `backend` sur MVP-16** — Alertes d’échéance MVP (3 tests service, 6 tests repository, 4 tests integration)
6. **✅ LIVRÉ : `frontend` sur MVP-17** — Centre d’alertes minimal intégré (widget dashboard, tableau, acquittement)
7. **✅ LIVRÉ : `backend` sur MVP-18** — Génération PDF administratif simple (service, command, 3 integration tests, 54 total tests passing)
8. **✅ LIVRÉ : `frontend` sur MVP-19** — Intégration bouton génération PDF dans écrans concession, hook usePdfGeneration, affichage chemin fichier et états d'erreur
9. **🚀 PROCHAIN : Lancer `backend` sur MVP-20** — Sauvegarde/restauration locale, dépendance `MVP-09` ✅
10. ~~Lancer `mapping` sur MVP-14~~ **✅ MVP-14 TERMINÉ** → Rendu + sélection ✅, intégration avec API Tauri réelle (MVP-10/11 ✅) peut démarrer.

## Indicateur de readiness

- Projet prêt pour lancer `backend` : **oui, prêt pour MVP-20** (sauvegarde/restauration locale), `MVP-09` ✅.
- Projet prêt pour lancer `frontend` : **MVP-19 TERMINÉ ✅** ; aucun lot frontend MVP immédiat avant les dépendances ultérieures de roadmap.
- Projet prêt pour lancer `mapping` : **✅ MVP-14 TERMINÉ**, composant rendu SVG + sélection implémentés avec 25 tests passants ; intégration réelle dépend de MVP-10/11.
- Projet prêt pour lancer `packaging` : oui, après sortie de MVP-01 ✅ puis MVP-02.
- Projet prêt pour lancer `qa` Phase 1 (MVP-24, MVP-25, MVP-26) : oui, MVP-03 stratégie livrée sans exécution complète de tests, backend MVP-04+ en cours.
