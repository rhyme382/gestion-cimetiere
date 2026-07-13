# ALPHA_ROADMAP

Date d'audit : 2026-07-11

## Positionnement

Le premier audit `alpha-recovery` reste le backlog de remise en etat immediat. La presente roadmap reprend cette logique pour la phase `ALPHA-0`, puis l etend vers le produit municipal final jusqu a `POST-BETA`.

## Phases de livraison

### ALPHA-0 — Reparer les parcours fondamentaux actuels
- livrer les parcours UI manquants pour cimetières, concessions, défunts, inhumations et recherche ;
- remplacer la cartographie mockée par une consultation réelle ;
- fiabiliser sauvegarde/restauration et les chemins de stockage ;
- rendre utilisables les échéances et le renouvellement minimal.

### ALPHA-1 — Exploitation metier minimale
- stabiliser le référentiel communal ;
- rendre exploitables emplacements, concessions, titulaires, défunts, inhumations et recherche globale ;
- activer tableau de bord, paramètres communaux et packaging de premier usage.

### ALPHA-2 — Procedures administratives et reglementaires
- couvrir espaces cinéraires, ayants droit, exhumations, réductions, urnes, mouvements ;
- livrer procédures de reprise, documents administratifs, pièces jointes et propagation des paramètres ;
- introduire tarifs, paiements et preuves réglementaires.

### BETA-1 — Fonctions avancees
- édition cartographique ;
- modèles documentaires, publipostage, historique ;
- statistiques avancées, dédoublonnage, historiques de mouvements.

### BETA-2 — Securite, import, audit et deploiement complet
- utilisateurs, rôles, habilitations ;
- journal d audit ;
- import CSV/Excel avec staging ;
- RGPD, export, conservation ;
- mise à jour applicative et validation QA des builds Windows/Linux.

### POST-BETA — Fonctions secondaires ou assistance avancee
- aide embarquée ;
- onboarding ;
- bundle de support et diagnostic administrateur.

## Dependances racines

- `FP-001` — Modeler le referentiel communal et les fiches cimetieres (Referentiel communal et cimetieres, backend)
- `FP-013` — Modeler les roles de titulaire cotitulaire et concessionnaire (Titulaires, cotitulaires et concessionnaires, backend)
- `FP-070` — Modeler les utilisateurs locaux roles et sessions (Utilisateurs, roles et habilitations, security)
- `FP-076` — Migrer la base et les sauvegardes vers des repertoires applicatifs OS avec metadonnees d integrite (Sauvegarde, restauration et integrite, backend)

## Correction explicite du sens des dependances

- `FP-014` (lier titulaires et concessions) precede `FP-015` (UI titulaires).
- `FP-023` (workflow backend inhumation complet) precede `FP-024` (UI inhumation).
- `FP-037` (donnees cartographiques reelles) precede `FP-038` (carte reelle) puis `FP-039` (localisation depuis la recherche).
- `FP-077` (restauration backend fiable) precede `FP-078` (UI de sauvegarde/restauration).
- `FP-070` et `FP-073` precede toute promesse serieuse de securite, audit et RGPD.

## Premier chemin critique recommande

1. `FP-001` — modeler le référentiel communal et les fiches cimetières.
2. `FP-004` — modeler la hiérarchie sections/carrés/rangées/emplacements.
3. `FP-005` — implémenter le CRUD backend des emplacements et statuts.
4. `FP-010` — modeler le contrat de concession et son cycle de vie.
5. `FP-011` — implémenter les workflows backend des concessions.
6. `FP-013` — modeler les rôles titulaires/cotitulaires/concessionnaires.
7. `FP-014` — associer les titulaires aux concessions.
8. `FP-019` — modeler l identité civile complète des défunts.
9. `FP-020` — implémenter les workflows backend des défunts.
10. `FP-022` puis `FP-023` — fiabiliser l inhumation et le lien défunt/concession/emplacement.
11. `FP-037` puis `FP-038` — brancher la cartographie réelle.
12. `FP-002`, `FP-006`, `FP-012`, `FP-021`, `FP-024`, `FP-045`, `FP-078` — livrer les parcours UI fondamentaux.

## Volumetrie du backlog

- `ALPHA-0` : 12 taches
- `ALPHA-1` : 25 taches
- `ALPHA-2` : 24 taches
- `BETA-1` : 12 taches
- `BETA-2` : 14 taches
- `POST-BETA` : 3 taches