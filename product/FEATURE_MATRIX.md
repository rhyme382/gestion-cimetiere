# Feature Matrix

Date d'audit : 2026-07-11

## Positionnement de ce second audit

Le premier audit `alpha-recovery` reste valable comme backlog de remise en etat Alpha-0.
Ce second audit vise autre chose : le produit municipal complet cible, comparable aux logiciels de reference cites dans `SPEC.md`, et non seulement la remise en etat du code actuel.

## Regle de preuve retenue

Une fonctionnalite n'est comptee comme presente que si un agent de mairie peut l'utiliser dans l'application packagee, avec persistance reelle, respect des regles metier, acces sans terminal et preuve utilisateur possible.

## Matrice cible vs etat observe

| Domaine | Portee cible finale | Etat du produit actuel package | Phase dominante | Taches ancrage |
| --- | --- | --- | --- | --- |
| Referentiel communal et cimetieres | Multi-cimetières, identité communale, horaires, règlement, plans, notes et photos. | Page Cimetières placeholder, pas de CRUD packagé. | ALPHA-1, ALPHA-0, BETA-1 | FP-001, FP-002, FP-003 |
| Sections, carres, rangees et emplacements | Maillage spatial complet, capacités, statuts et disponibilité exploitable. | Structure réduite aux plots simples ; pas de gestion UI réelle. | ALPHA-1 | FP-004, FP-005, FP-006 |
| Columbariums, cavurnes, ossuaires et jardins du souvenir | Gestion distincte des espaces cinéraires et mémoriels. | Aucun support métier distinct hors type théorique dans SPEC. | ALPHA-1, ALPHA-2 | FP-007, FP-008, FP-009 |
| Concessions | Cycle de vie complet : création, renouvellement, conversion, clôture, archive. | Lecture partielle seulement ; creation et edition non branchées. | ALPHA-1, ALPHA-0 | FP-010, FP-011, FP-012 |
| Titulaires, cotitulaires et concessionnaires | Rôles juridiques différenciés et historisés. | Personnes réduites à name/email/phone/role sans lien riche. | ALPHA-1 | FP-013, FP-014, FP-015 |
| Ayants droit, heritiers et liens familiaux | Réseau familial, preuves et statuts successoraux. | Absent. | ALPHA-2 | FP-016, FP-017, FP-018 |
| Defunts | Identité civile complète, décès, rattachements et historique. | Lecture partielle ; creation et navigation incomplètes. | ALPHA-1, ALPHA-0 | FP-019, FP-020, FP-021 |
| Inhumations | Enregistrement réglementé avec contrôles de capacité et autorisations. | Commande minimale existante sans parcours UI complet. | ALPHA-1, ALPHA-0 | FP-022, FP-023, FP-024 |
| Exhumations | Demande, autorisation, exécution et destination. | Absent. | ALPHA-2 | FP-025, FP-026, FP-027 |
| Reductions et reunions de corps | Opérations distinctes avec traçabilité des restes. | Absent. | ALPHA-2, BETA-1 | FP-028, FP-029, FP-030 |
| Urnes, depots, retraits et dispersions | Cycle complet des urnes et dispersions. | Absent. | ALPHA-2 | FP-031, FP-032, FP-033 |
| Transferts et mouvements funeraires | Journal unifié des mouvements de corps et d urnes. | Absent. | ALPHA-2, BETA-1 | FP-034, FP-035, FP-036 |
| Cartographie de consultation | Localisation réelle des emplacements, concessions et défunts. | Carte mockée, non connectée à SQLite. | ALPHA-0, ALPHA-1 | FP-037, FP-038, FP-039 |
| Cartographie editable | Edition des géométries, publication et versioning des plans. | Absent. | BETA-1 | FP-040, FP-041, FP-042 |
| Echeances et renouvellements | Calcul d échéance, relances, renouvellements et états. | Alertes partielles ; renouvellement UI absent. | ALPHA-1, ALPHA-0 | FP-043, FP-044, FP-045 |
| Procedures d abandon et de reprise | Dossier réglementaire complet avec délais et arrêtés. | Absent. | ALPHA-2 | FP-046, FP-047, FP-048 |
| Documents administratifs | Catalogue des documents municipaux générés depuis les dossiers. | Un seul PDF simple de fiche concession. | ALPHA-2 | FP-049, FP-050, FP-051 |
| Modeles, publipostage et historique documentaire | Modèles, fusion en lot, numérotation et historique. | Absent. | BETA-1 | FP-052, FP-053, FP-054 |
| Tarifs, redevances et paiements | Grilles tarifaires, encaissement, impayés et reçus. | Absent. | ALPHA-1 | FP-055, FP-056, FP-057 |
| Recherche multicritere et doublons | Recherche transversale, ouverture des résultats, détection de doublons. | Recherche simple fragile, ouverture résultats incomplète. | ALPHA-1, BETA-1, ALPHA-0 | FP-058, FP-059, FP-060 |
| Tableaux de bord, statistiques et editions | KPI métier, éditions imprimables et analyses par période. | Dashboard partiel, compteurs incomplets. | ALPHA-1, BETA-1 | FP-061, FP-062, FP-063 |
| Import CSV/Excel et reprise de donnees | Assistant d import, staging, validation, rollback. | Absent. | BETA-2 | FP-064, FP-065, FP-066 |
| Documents joints et photographies | Pièces attachées, prévisualisation et sauvegarde avec la base. | Absent. | ALPHA-2 | FP-067, FP-068, FP-069 |
| Utilisateurs, roles et habilitations | Profils locaux, restrictions d actions et administration. | Absent. | BETA-2 | FP-070, FP-071, FP-072 |
| Journal d audit et tracabilite | Traçabilité immuable des actions et exports. | Absent. | BETA-2 | FP-073, FP-074, FP-075 |
| Sauvegarde, restauration et integrite | Sauvegarde locale fiable, restauration validée, preuves d intégrité. | Backend existant mais contrat UI cassé et stockage à fiabiliser. | ALPHA-0 | FP-076, FP-077, FP-078 |
| Parametrage communal | Identité de la commune, durées, alertes, types, couleurs et modèles. | Page Paramètres placeholder. | ALPHA-1, ALPHA-2 | FP-079, FP-080, FP-081 |
| Packaging, installation et mises a jour | Installateurs prouvés, premier démarrage guidé, upgrade maîtrisé. | Configuration présente, usage final packagé non prouvé. | ALPHA-1, BETA-2 | FP-082, FP-083, FP-084 |
| RGPD, export et conservation | Politiques de conservation, export, archivage, anonymisation. | Absent. | BETA-2 | FP-085, FP-086, FP-087 |
| Aide, documentation et accompagnement utilisateur | Aide embarquée, onboarding et bundle de support. | Documentation technique présente, aide embarquée absente. | POST-BETA | FP-088, FP-089, FP-090 |

## Lectures transverses majeures

- Le frontend actuel prouve surtout des parcours de consultation partiels : concessions, defunts, alertes, PDF simple et carte de demonstration.
- Le backend actuel couvre un noyau CRUD limite a `cemeteries`, `plots`, `concessions`, `individuals`, `burials` et `alerts`.
- Le schema SQLite actuel ne couvre pas les pieces jointes, les procedures, les utilisateurs, le journal d audit, les tarifs, les imports ni la conservation RGPD.
- Les rapports QA et release sont utiles comme indices, mais plusieurs se contredisent ou restent documentaires ; ils ne suffisent pas a prouver l usage municipal complet.