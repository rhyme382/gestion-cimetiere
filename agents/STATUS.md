# Statut des agents

Date de référence : 2026-06-16

## Vue d'ensemble

| Agent | Domaine | Statut | Livrable attendu | Dépendances |
| --- | --- | --- | --- | --- |
| orchestrator | Pilotage | En cours | Roadmap MVP, backlog atomique, dépendances, suivi global | SPEC.md |
| frontend | Interface React/Tauri | ✅ MVP-12/13/15/17/19/26A livré | Shell ✅, UI ✅, API ✅, dashboard ✅, listes ✅, fiches ✅, recherche ✅, cartographie ✅, alertes ✅, PDF export ✅, E2E infrastructure ✅ | MVP-01 ✅, MVP-05A ✅, MVP-10 ✅, MVP-11 ✅, MVP-14 ✅, MVP-16 ✅, MVP-18 ✅, MVP-20 ✅ |
| backend | Modèle métier et persistance | ✅ MVP-10/11/16/18/20 livré | Commandes Tauri CRUD ✅, alertes d'échéance ✅, PDF administratif ✅, sauvegarde/restauration ✅, vues métier complètes ✅ | MVP-05 ✅, MVP-09 (migrations) ✅ |
| mapping | Cartographie cimetière | ✅ Phase 3 terminée | Format de plan MVP ✅, rendu simple ✅, sélection d’emplacement ✅ | MVP-04 ✅, MVP-07 ✅, MVP-14 ✅ |
| packaging | Distribution poste mairie | **✅ MVP-21/22/23 LIVRÉ** | Config Tauri NSIS ✅, AppImage ✅, .deb ✅ ; docs packaging multi-plateforme ✅ | MVP-01 ✅, MVP-02 ✅, MVP-20 ✅ |
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
| Phase 4 — Documents, alertes, sauvegarde | ✅ Terminé | 100% (alertes ✅, PDF ✅, sauvegarde ✅) |
| Phase 5 — Packaging et validation | **✅ Terminée (MVP-21/22/23 ✅)** | 100% (Windows NSIS ✅, AppImage ✅, .deb ✅) |

## Checklist de lancement

- [x] Dépôt nettoyé et repositionné
- [x] Infrastructure d'orchestration initialisée
- [x] Prompts spécialisés pour tous les agents
- [x] SPEC.md complète et validée
- [x] ROADMAP.md avec backlog priorisé
- [x] `agents/STATUS.md` défini comme suivi officiel
- [x] Rapports MVP-00, MVP-01, MVP-02, MVP-03, MVP-04, MVP-05, MVP-05A, MVP-06, MVP-07, MVP-08, MVP-10, MVP-11, MVP-12, MVP-13, MVP-14, MVP-15, MVP-16, MVP-17, MVP-18, MVP-19, MVP-20, MVP-21, MVP-22, MVP-23, MVP-26A
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
- [x] Exécution MVP-20 — ✅ Sauvegarde/restauration locale (service, commands, 8 integration tests)
- [x] Exécution MVP-21 — ✅ Packaging Windows NSIS (configuration Tauri, icônes .ico, documentation build)
- [x] Exécution MVP-22 — ✅ Packaging Linux AppImage (configuration Tauri multi-cible, documentation AppImage)
- [x] Exécution MVP-23 — ✅ Packaging Linux .deb (configuration Tauri triple-cible, documentation Debian/Ubuntu)
- [x] Exécution MVP-26A — ✅ Infrastructure E2E Playwright + SauvegardesPage UI (déverrouille MVP-26)

## Corrections et blocages récents

### Corrections appliquées
- **MVP-20 (2026-06-17)** : ✅ Test isolation corrigée — Implémentation TempDir pour isolation par test au lieu de `--test-threads=1`. Tous les 91 tests passent en mode parallèle normal. MVP-24 peut être relancé.

### Blocages actuels
- **MVP-26 (2026-06-17)** : ✅ **DÉVERROUILLÉ par MVP-26A** — Infrastructure E2E (Playwright 1.61.0 ✅) + SauvegardesPage UI ✅ + Navigation ✅ maintenant en place. Prêt pour écrire les 9 tests E2E (MVP-26).
- Aucun prompt spécialisé manquant identifié.
- **MAPPING DÉBLOQUÉ** : MVP-07 (format cartographique) stabilisé ; MVP-14 (rendu) peut démarrer après MVP-02 ✅ et contrats Tauri stubs.
- Le lancement parallèle doit respecter les dépendances d’entrée suivantes :
  - `backend` démarre immédiatement sur MVP-00 et MVP-01 ;
  - `qa` démarre dès que MVP-01 est cadré ;
  - `frontend` attend la stabilisation de MVP-01 puis MVP-05A pour les vues métier ;
  - `mapping` peut démarrer sur MVP-14 dès que MVP-07 ✅ + MVP-02 ✅ en place ;
  - `packaging` peut cadrer sa stratégie après MVP-01 et lancer les builds sur squelette après MVP-02.

## Prochaine étape recommandée

**🎯 MVP-27 TERMINÉ — PROJECT RELEASE READY 🎯**

All phases complete:
1. ✅ Phase 0 — Socle (MVP-00 à MVP-08)
2. ✅ Phase 1 — Noyau métier (MVP-09 à MVP-11)
3. ✅ Phase 2 — Interface (MVP-12 à MVP-13)
4. ✅ Phase 3 — Cartographie (MVP-14 à MVP-15)
5. ✅ Phase 4 — Documents/alertes/sauvegarde (MVP-16 à MVP-20)
6. ✅ Phase 5 — Packaging (MVP-21 à MVP-23)
7. ✅ Validation E2E (MVP-26A à MVP-26B)
8. ✅ Audit final release (MVP-27)

**Verdict :** 🟢 **MVP_RELEASE_READY_FOR_PILOT**

Voir reports/qa/mvp27_final_release_audit.md pour audit complet (10/10 critères passants).

## Indicateur de readiness

- Projet prêt pour lancer `backend` : **MVP-20 ✅ LIVRÉ avec correction isolation** (sauvegarde/restauration locale + TempDir test isolation) ; prochain = **MVP-24 relançable** (QA massive tests noyau métier).
- Projet prêt pour lancer `frontend` : **MVP-19 TERMINÉ ✅** ; prochain lot frontend dépend de nouvelles fonctionnalités roadmap.
- Projet prêt pour lancer `mapping` : **✅ MVP-14 TERMINÉ**, composant rendu SVG + sélection implémentés avec 25 tests passants ; intégration réelle dépend de MVP-10/11.
- Projet prêt pour lancer `packaging` : **✅ MVP-21/22/23 LIVRÉ** (Phase 5 Packaging 100% : NSIS ✅ + AppImage ✅ + .deb ✅) ; prêt pour MVP-26 tests E2E.
- Projet prêt pour lancer `qa` Phase 1 (MVP-24, MVP-25, MVP-26) : **✅ Oui**, MVP-03 stratégie livrée, backend MVP-04+ ✅, MVP-11 ✅, MVP-16 ✅, MVP-20 ✅ prêts.
