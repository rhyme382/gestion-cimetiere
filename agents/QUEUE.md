# File de tâches MVP

Date de référence : 2026-06-15

## Tâches prêtes à lancer immédiatement

### MVP-00 — Stabiliser la structure du dépôt et les conventions de modules

Statut : backlog
Responsable : backend
Priorité : haute
Module : backend
Dépend de : aucune

### Objectif
Définir l’organisation minimale du projet desktop, backend local, packages partagés et tests.

### Critères d’acceptation
- [ ] structure cible explicitée
- [ ] conventions de nommage fixées
- [ ] périmètre des modules documenté
- [ ] aucun code métier développé hors cadrage

### MVP-02 — Initialiser le shell Tauri + React + TypeScript

Statut : backlog
Responsable : frontend
Priorité : haute
Module : frontend
Dépend de : MVP-01

### Objectif
Poser le socle applicatif desktop et le shell de navigation sans développer les écrans métier complets.

### Critères d’acceptation
- [ ] shell desktop initialisé
- [ ] routage de base en place
- [ ] structure frontend documentée
- [ ] tests initiaux prévus

### MVP-03 — Définir la stratégie de tests du MVP

Statut : backlog
Responsable : qa
Priorité : haute
Module : tests
Dépend de : MVP-01

### Objectif
Définir les suites, jeux de données et critères de validation MVP.

### Critères d’acceptation
- [ ] pyramide de tests définie
- [ ] scénarios critiques listés
- [ ] jeux de données de référence cadrés
- [ ] stratégie de validation des agents documentée

## Backlog complet par ordre de priorité

| ID | Agent | Priorité | Dépend de | Tâche atomique |
| --- | --- | --- | --- | --- |
| MVP-00 | backend | haute | aucune | Stabiliser la structure du dépôt et les conventions de modules |
| MVP-01 | backend | haute | MVP-00 | Définir l’architecture applicative du workspace desktop |
| MVP-02 | frontend | haute | MVP-01 | Initialiser le shell Tauri + React + TypeScript |
| MVP-03 | qa | haute | MVP-01 | Définir la stratégie de tests du MVP |
| MVP-04 | backend | haute | MVP-01 | Définir le schéma SQLite MVP et les entités cœur |
| MVP-05 | backend | haute | MVP-04 | Définir les contrats API/Tauri et les DTO partagés |
| MVP-05A | backend | haute | MVP-05 | Générer automatiquement les types TypeScript à partir des modèles Rust |
| MVP-06 | frontend | haute | MVP-02, MVP-05A | Mettre en place la base de composants UI et le shell de navigation |
| MVP-07 | mapping | haute | MVP-04 | Définir le format cartographique MVP |
| MVP-08 | packaging | haute | MVP-01 | Définir la stratégie de packaging Windows/Linux |
| MVP-09 | backend | haute | MVP-04 | Implémenter les migrations initiales et les fixtures MVP |
| MVP-10 | backend | haute | MVP-05, MVP-09 | Implémenter les commandes Tauri pour cimetières et emplacements |
| MVP-11 | backend | haute | MVP-05, MVP-09 | Implémenter les commandes Tauri pour concessions, personnes et défunts |
| MVP-12 | frontend | haute | MVP-05A, MVP-06, MVP-10, MVP-11 | Créer dashboard, liste concessions et fiche concession |
| MVP-13 | frontend | haute | MVP-06, MVP-11 | Créer liste défunts, fiche défunt et recherche globale simple |
| MVP-14 | mapping | haute | MVP-07, MVP-10 | Implémenter le rendu cartographique simple et la sélection d’emplacement |
| MVP-15 | frontend | moyenne | MVP-12, MVP-13, MVP-14 | Relier cartographie, concession et défunt côté interface |
| MVP-16 | backend | moyenne | MVP-11 | Implémenter les alertes d’échéance MVP |
| MVP-17 | frontend | moyenne | MVP-12, MVP-16 | Intégrer le centre d’alertes minimal dans l’interface |
| MVP-18 | backend | moyenne | MVP-11 | Générer un PDF administratif simple |
| MVP-19 | frontend | moyenne | MVP-12, MVP-18 | Préparer l’écran d’export PDF simple |
| MVP-20 | backend | haute | MVP-09 | Implémenter sauvegarde/restauration locale |
| MVP-21 | packaging | moyenne | MVP-02, MVP-20 | Préparer le packaging Windows NSIS |
| MVP-22 | packaging | moyenne | MVP-02, MVP-20 | Préparer le packaging Linux AppImage |
| MVP-23 | packaging | basse | MVP-22 | Préparer le packaging Linux `.deb` |
| MVP-24 | qa | haute | MVP-09, MVP-11, MVP-16, MVP-20 | Créer les jeux de données et tests backend du noyau métier |
| MVP-25 | qa | haute | MVP-12, MVP-13, MVP-17 | Créer les tests frontend des vues MVP |
| MVP-26 | qa | haute | MVP-15, MVP-19, MVP-21, MVP-22 | Créer les tests E2E des flux critiques |
| MVP-27 | qa | haute | MVP-24, MVP-25, MVP-26 | Exécuter l’audit QA de readiness MVP |

## Répartition par agent

### frontend

- MVP-02
- MVP-06
- MVP-12
- MVP-13
- MVP-15
- MVP-17
- MVP-19

### backend

- MVP-00
- MVP-01
- MVP-04
- MVP-05
- MVP-05A
- MVP-09
- MVP-10
- MVP-11
- MVP-16
- MVP-18
- MVP-20

### mapping

- MVP-07
- MVP-14

### packaging

- MVP-08
- MVP-21
- MVP-22
- MVP-23

### qa

- MVP-03
- MVP-24
- MVP-25
- MVP-26
- MVP-27

## Dépendances critiques

- `frontend` ne doit pas lancer les vues métier avant MVP-05A.
- `mapping` ne doit pas figer le rendu avant MVP-07 et le modèle emplacement de MVP-10.
- `packaging` peut cadrer sa stratégie avant le métier, mais les builds finaux dépendent de MVP-02 et MVP-20.
- `qa` démarre dès MVP-03, puis bloque la readiness finale via MVP-27.
