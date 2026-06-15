# Roadmap Projet

Date de référence : 2026-06-15

## Vérification de cohérence globale

Le projet est cohérent avec le cahier des charges et l’infrastructure d’orchestration initialisée.

Points confirmés :
- cible desktop locale adaptée au besoin mairie ;
- documentation de pilotage en place ;
- prompts spécialisés disponibles pour `frontend`, `backend`, `mapping`, `packaging` et `qa` ;
- dépôt nettoyé vers un périmètre versionnable ;
- priorité donnée au MVP avant modules avancés comme portail public, OCR, cloud et mobile.

Points de vigilance :
- le périmètre du cahier des charges est très large et doit rester strictement borné au MVP ;
- la cartographie doit rester simple au MVP pour éviter de bloquer le noyau métier ;
- la génération documentaire doit commencer par un PDF simple ;
- le packaging doit démarrer tôt pour éviter une dérive de fin de projet.

## Validation de l’architecture cible

Architecture retenue : adaptée au projet.

- `Tauri` : bon choix pour une application municipale locale légère, Windows/Linux, avec packaging natif.
- `React` : adapté pour une interface métier riche et modulaire.
- `TypeScript` : nécessaire pour sécuriser les contrats UI et les modèles d’entrée/sortie.
- `SQLite` : adapté au mode hors ligne et à une exploitation mono-poste ou petit collectif local.
- `NSIS` : adapté à l’exigence d’un installateur Windows propre.
- `AppImage + .deb` : compromis raisonnable pour Linux, avec AppImage pour la portabilité et `.deb` pour les déploiements classiques.

Décisions complémentaires de cadrage :
- backend local en Rust via commandes Tauri ;
- tests frontend avec Vitest ;
- tests E2E avec Playwright ;
- tests backend avec `cargo test` ;
- cartographie MVP sur une base légère compatible Tauri ; ne pas introduire de dépendance SIG lourde au départ.

## Définition du MVP

Le MVP couvre uniquement les capacités nécessaires pour exploiter un premier poste mairie local :

1. socle desktop Tauri opérationnel sous Windows et Linux ;
2. base SQLite locale avec migrations ;
3. gestion minimale des cimetières, emplacements, concessions, personnes et défunts ;
4. association défunt/concession/emplacement ;
5. tableau de bord minimal ;
6. listes et fiches concessions et défunts ;
7. recherche globale simple ;
8. cartographie simple avec affichage d’emplacements et sélection ;
9. alertes d’échéance minimales ;
10. génération d’un PDF administratif simple ;
11. sauvegarde/restauration locale ;
12. packaging Windows NSIS et Linux AppImage + `.deb` ;
13. base de tests unitaires, intégration et E2E sur les flux critiques.

Hors MVP :
- portail public ;
- OCR ;
- cloud/synchronisation ;
- application mobile ;
- gestion avancée des rôles ;
- import Excel complet ;
- statistiques avancées ;
- QR codes ;
- procédure complète de reprise avec toutes variantes réglementaires.

## Phases de livraison

### Phase 0 — Pilotage et socle

- finaliser roadmap, backlog et statut ;
- stabiliser la structure du dépôt ;
- poser le squelette Tauri + React + TypeScript ;
- poser les outils de test ;
- préparer les conventions de packaging.

### Phase 1 — Noyau métier MVP

- définir le schéma SQLite MVP ;
- créer les migrations initiales ;
- implémenter les entités cœur ;
- exposer les premières commandes Tauri ;
- couvrir les règles métier de base.

### Phase 2 — Interface métier MVP

- créer le shell applicatif ;
- mettre en place les routes principales ;
- livrer dashboard minimal, listes et fiches MVP ;
- intégrer la recherche globale simple.

### Phase 3 — Cartographie MVP

- définir le format de plan minimal ;
- afficher les emplacements et leurs statuts ;
- lier la sélection cartographique aux données métier ;
- permettre la localisation d’une concession ou d’un défunt.

### Phase 4 — Documents, alertes et sauvegarde

- générer un PDF simple ;
- calculer les alertes d’échéance MVP ;
- préparer sauvegarde et restauration locales ;
- compléter les tests de non-régression métier.

### Phase 5 — Packaging et validation finale

- produire le build Windows avec NSIS ;
- produire le build Linux AppImage ;
- produire le build Linux `.deb` si le pipeline est stable ;
- exécuter la validation QA de bout en bout ;
- préparer le lancement du premier cycle d’intégration.

## Backlog MVP priorisé

| ID | Tâche | Agent | Priorité | Dépend de |
| --- | --- | --- | --- | --- |
| MVP-00 | Stabiliser la structure du dépôt et les conventions de modules | backend | haute | aucune |
| MVP-01 | Définir l’architecture applicative du workspace desktop | backend | haute | MVP-00 |
| MVP-02 | Initialiser le shell Tauri + React + TypeScript | frontend | haute | MVP-01 |
| MVP-03 | Définir la stratégie de tests du MVP | qa | haute | MVP-01 |
| MVP-04 | Définir le schéma SQLite MVP et les entités cœur | backend | haute | MVP-01 |
| MVP-05 | Définir les contrats API/Tauri et les DTO partagés | backend | haute | MVP-04 |
| MVP-05A | Générer automatiquement les types TypeScript à partir des modèles Rust | backend | haute | MVP-05 |
| MVP-06 | Mettre en place la base de composants UI et le shell de navigation | frontend | haute | MVP-02, MVP-05A |
| MVP-07 | Définir le format cartographique MVP | mapping | haute | MVP-04 |
| MVP-08 | Définir la stratégie de packaging Windows/Linux | packaging | haute | MVP-01 |
| MVP-09 | Implémenter les migrations initiales et les fixtures MVP | backend | haute | MVP-04 |
| MVP-10 | Implémenter les commandes Tauri pour cimetières et emplacements | backend | haute | MVP-05, MVP-09 |
| MVP-11 | Implémenter les commandes Tauri pour concessions, personnes et défunts | backend | haute | MVP-05, MVP-09 |
| MVP-12 | Créer les écrans dashboard, liste concessions, fiche concession | frontend | haute | MVP-05A, MVP-06, MVP-10, MVP-11 |
| MVP-13 | Créer les écrans liste défunts, fiche défunt, recherche globale simple | frontend | haute | MVP-06, MVP-11 |
| MVP-14 | Implémenter le rendu cartographique simple et la sélection d’emplacement | mapping | haute | MVP-07, MVP-10 |
| MVP-15 | Relier cartographie, concession et défunt côté interface | frontend | moyenne | MVP-12, MVP-13, MVP-14 |
| MVP-16 | Implémenter les alertes d’échéance MVP | backend | moyenne | MVP-11 |
| MVP-17 | Intégrer le centre d’alertes minimal dans l’interface | frontend | moyenne | MVP-12, MVP-16 |
| MVP-18 | Générer un PDF administratif simple | backend | moyenne | MVP-11 |
| MVP-19 | Préparer l’écran d’export PDF simple | frontend | moyenne | MVP-12, MVP-18 |
| MVP-20 | Implémenter sauvegarde/restauration locale | backend | haute | MVP-09 |
| MVP-21 | Préparer le packaging Windows NSIS | packaging | moyenne | MVP-02, MVP-20 |
| MVP-22 | Préparer le packaging Linux AppImage | packaging | moyenne | MVP-02, MVP-20 |
| MVP-23 | Préparer le packaging Linux `.deb` | packaging | basse | MVP-22 |
| MVP-24 | Créer les jeux de données et tests backend du noyau métier | qa | haute | MVP-09, MVP-11, MVP-16, MVP-20 |
| MVP-25 | Créer les tests frontend des vues MVP | qa | haute | MVP-12, MVP-13, MVP-17 |
| MVP-26 | Créer les tests E2E des flux critiques | qa | haute | MVP-15, MVP-19, MVP-21, MVP-22 |
| MVP-27 | Exécuter l’audit QA de readiness MVP | qa | haute | MVP-24, MVP-25, MVP-26 |

## Dépendances structurantes

- Le backend doit cadrer la structure, le schéma et les contrats avant le développement des vues métier.
- Le frontend peut démarrer le shell et le design system dès que l’architecture de workspace est fixée.
- Le mapping peut démarrer dès que le format des emplacements et les données minimales sont stabilisés.
- Le packaging peut démarrer tôt sur le squelette applicatif ; il ne doit pas attendre la fin du métier.
- La QA doit définir les attentes dès le début, puis industrialiser les suites au fur et à mesure.

## Préparation au lancement simultané des agents

Statut de préparation :
- `frontend` : prêt, sous réserve que `backend` livre d’abord la structure et les contrats MVP ;
- `backend` : prêt immédiatement ;
- `mapping` : prêt, sous réserve que `backend` fixe le format des emplacements ;
- `packaging` : prêt dès qu’un squelette Tauri minimal existe ;
- `qa` : prêt immédiatement pour définir la stratégie et les jeux de tests.

Prompts manquants :
- aucun prompt spécialisé manquant identifié à ce stade.
