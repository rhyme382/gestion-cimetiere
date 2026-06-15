# Statut du projet — Gestion Cimetière MVP

**Dernière mise à jour :** 2026-06-15

## Vue d'ensemble

Le projet Gestion Cimetière est en phase **d'orchestration et définition d'architecture**. L'infrastructure de pilotage est en place, les agents sont coordonnés, et le lancement des MVPs est imminent.

| Phase | Statut | Avancement |
| --- | --- | --- |
| Phase 0 — Pilotage et socle | ✅ En cours | 70% |
| Phase 1 — Noyau métier MVP | 🚀 À lancer | 0% |
| Phase 2 — Interface métier MVP | 🔄 Dépendant de Phase 1 | 0% |
| Phase 3 — Cartographie MVP | 🔄 Dépendant de Phase 1 | 0% |
| Phase 4 — Documents, alertes, sauvegarde | 🔄 Dépendant de Phase 2 | 0% |
| Phase 5 — Packaging et validation | 🔄 Dépendant de Phase 4 | 0% |

## MVPs en focus

### Backend — Tâches prioritaires (MVP-00 à MVP-05A)

| MVP | Objectif | Dépend | Statut |
| --- | --- | --- | --- |
| **MVP-00** | Stabiliser dépôt et conventions | — | 📋 Défini |
| **MVP-01** | Définir architecture applicative | MVP-00 | 📋 Défini |
| **MVP-04** | Schéma SQLite et entités | MVP-01 | 📋 Défini |
| **MVP-05** | Contrats API/Tauri et DTOs | MVP-04 | 📋 Défini |
| **MVP-05A** | Génération types TypeScript | MVP-05 | 📋 Défini |

**Livrables attendus :** Rapports de définition dans `reports/dev/MVP-XX.md`

## Checklist de lancement

- [x] Dépôt nettoyé et repositionné
- [x] Infrastructure d'orchestration initialisée
- [x] Prompts spécialisés pour tous les agents
- [x] SPEC.md complète et validée
- [x] ROADMAP.md avec backlog priorisé
- [x] agents/STATUS.md avec dépendances
- [x] Rapports MVP-00, MVP-01, MVP-04, MVP-05, MVP-05A
- [ ] Exécution MVP-00 (backend)
- [ ] Exécution MVP-01 (backend)
- [ ] Exécution MVP-04 (backend)
- [ ] Exécution MVP-05 (backend)
- [ ] Exécution MVP-05A (backend)

## Blocages connus

Aucun à ce stade.

## Documentation de référence

- **SPEC.md** — Cahier des charges complet
- **ROADMAP.md** — Phases et backlog priorisé
- **AGENTS.md** — Définition et responsabilités des agents
- **orchestration/prompts/** — Prompts spécialisés par agent
- **agents/STATUS.md** — Statut détaillé par agent
- **reports/dev/** — Rapports de définition MVP

## Prochaines actions

1. Lancer `backend` sur **MVP-00** (stabiliser dépôt)
2. Lancer `backend` sur **MVP-01** (définir architecture)
3. Paralléliser :
   - `backend` sur **MVP-04** (schéma SQLite)
   - `qa` sur cadrage stratégie tests
   - `packaging` sur cadrage stratégie Windows/Linux
