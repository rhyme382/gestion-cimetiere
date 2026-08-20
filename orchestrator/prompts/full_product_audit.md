Tu dois maintenant réaliser un second audit produit, distinct du précédent.

Le premier audit a correctement identifié les écarts entre l’application actuelle et une alpha utilisable, mais il a produit seulement 15 tâches réparties dans 4 couches techniques.

Ce résultat constitue un backlog de remise en état Alpha 0, pas le backlog exhaustif du logiciel métier complet recherché.

Ne supprime pas et ne dévalorise pas le premier audit.

Lis impérativement :

- SPEC.md ;
- ROADMAP.md ;
- product/audits/alpha-recovery/FEATURE_MATRIX.md ;
- product/audits/alpha-recovery/GAP_ANALYSIS.md ;
- product/audits/alpha-recovery/USER_JOURNEYS.md ;
- tasks/archive/backlog-alpha-recovery.json ;
- tous les éléments du comparatif fonctionnel présent dans le dépôt ;
- le frontend ;
- le backend ;
- le schéma SQLite ;
- les rapports.

## Objectif

Construire le cahier des charges fonctionnel complet et le backlog exhaustif d’un logiciel municipal de gestion de cimetières comparable aux meilleurs logiciels étudiés.

Cette mission ne doit pas se limiter aux lacunes visibles du code actuel.

Elle doit couvrir la cible produit finale.

## Domaines métier obligatoires

Créer une couverture distincte au minimum pour :

1. Référentiel communal et cimetières
2. Sections, carrés, rangées et emplacements
3. Columbariums, cavurnes, ossuaires et jardins du souvenir
4. Concessions
5. Titulaires, cotitulaires et concessionnaires
6. Ayants droit, héritiers et liens familiaux
7. Défunts
8. Inhumations
9. Exhumations
10. Réductions et réunions de corps
11. Urnes, dépôts, retraits et dispersions
12. Transferts et mouvements funéraires
13. Cartographie de consultation
14. Cartographie éditable
15. Échéances et renouvellements
16. Procédures d’abandon et de reprise
17. Documents administratifs
18. Modèles, publipostage et historique documentaire
19. Tarifs, redevances et paiements
20. Recherche multicritère et doublons
21. Tableaux de bord, statistiques et éditions
22. Import CSV/Excel et reprise de données
23. Documents joints et photographies
24. Utilisateurs, rôles et habilitations
25. Journal d’audit et traçabilité
26. Sauvegarde, restauration et intégrité
27. Paramétrage communal
28. Packaging, installation et mises à jour
29. RGPD, export et conservation
30. Aide, documentation et accompagnement utilisateur

## Distinction obligatoire

Séparer deux champs :

- `domain` : domaine métier ;
- `recommended_agent` : frontend, backend, mapping, documents, qa, packaging, product, security.

Ne jamais utiliser frontend/backend comme domaine métier.

## Granularité

Chaque tâche doit être atomique.

Une tâche ne doit pas regrouper plusieurs opérations métier majeures.

Exemple interdit :

« Gérer concessionnaire, ayant droit et défunt »

Exemples corrects :

- créer un titulaire ;
- associer un titulaire à une concession ;
- ajouter un ayant droit ;
- enregistrer une inhumation ;
- transférer un défunt ;
- afficher l’historique des mouvements.

## Dépendances

Vérifier le sens réel des dépendances.

Les contrats et capacités backend doivent précéder les interfaces qui les utilisent.

Détecter et corriger notamment l’inversion actuelle autour d’ALPHA-014.

## Niveaux de livraison

Classer chaque tâche dans l’une des phases :

- ALPHA-0 : réparer les parcours fondamentaux actuels ;
- ALPHA-1 : exploitation métier minimale ;
- ALPHA-2 : procédures administratives et réglementaires ;
- BETA-1 : fonctionnalités avancées ;
- BETA-2 : sécurité, import, audit et déploiement complet ;
- POST-BETA : fonctions secondaires ou portail public.

## Livrables

Produire sans écraser les archives :

- product/TARGET_FEATURE_CATALOG.md
- product/FULL_PRODUCT_GAP_ANALYSIS.md
- product/FULL_USER_JOURNEYS.md
- product/FULL_PRODUCT_ROADMAP.md
- product/DOMAIN_MODEL.md
- tasks/full_backlog.json
- reports/product/FULL_PRODUCT_AUDIT_REPORT.md

## Exigences pour le backlog

Le backlog doit contenir vraisemblablement plusieurs dizaines de tâches, et probablement plus de 80 si le découpage est réellement atomique.

Ne fixe pas artificiellement le nombre, mais n’agrège pas les fonctions pour réduire le volume.

Chaque tâche doit comporter :

- id ;
- domain ;
- phase ;
- title ;
- user_story ;
- priority ;
- status ;
- dependencies ;
- recommended_agent ;
- likely_files ;
- acceptance_criteria ;
- required_unit_tests ;
- required_integration_tests ;
- required_e2e_test ;
- required_ui_evidence ;
- legal_or_business_rules ;
- definition_of_done.

## Règle de vérité

Une fonction n’est terminée que si :

- elle existe dans l’interface packagée ;
- elle persiste réellement ;
- elle respecte les règles métier ;
- elle est testée ;
- elle est accessible sans terminal ;
- une preuve utilisateur est fournie.

Ne modifie aucun code métier.

À la fin, fournir :

- nombre de domaines ;
- nombre de tâches ;
- nombre de tâches par phase ;
- nombre de tâches critiques ;
- dépendances racines ;
- premier chemin critique recommandé.
