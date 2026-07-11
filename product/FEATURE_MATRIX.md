# Feature Matrix

Date d'audit : 2026-07-11

Question de référence : un agent de mairie peut-il effectuer l'opération dans l'application packagée, sans terminal ?

## Verdict global

Le produit actuel est un prototype de consultation partielle, pas une alpha métier exploitable.

Fonctionnalités réellement utilisables aujourd'hui :
- consulter le shell de navigation ;
- consulter une liste de concessions ;
- ouvrir une fiche concession par lien de détail ;
- consulter une liste de défunts déjà présents ;
- lancer une recherche simple sur des personnes ;
- consulter le centre d'alertes si des alertes existent déjà ;
- générer un PDF simple depuis une fiche concession ;
- visualiser une cartographie de démonstration non reliée aux données réelles.

Fonctionnalités non réellement utilisables malgré la présence de code backend ou de pages :
- création, modification et suppression métier ;
- gestion réelle des cimetières ;
- gestion réelle des emplacements ;
- association concessionnaire / ayant droit / défunt depuis l'UI ;
- restauration de sauvegarde ;
- exploitation fiable des alertes en production ;
- parcours packagés prouvés sur installateurs Windows/AppImage/.deb.

## Matrice

| Domaine | Fonctionnalité attendue | État UI packagée | Verdict produit | Preuves lues |
| --- | --- | --- | --- | --- |
| Shell | Navigation entre pages principales | Sidebar et header présents | Oui | `src/components/layout/Sidebar.tsx`, `src/components/layout/Header.tsx`, `src/router.tsx` |
| Dashboard | Voir quelques compteurs | Compteurs partiels, "Alertes actives" figé à `—`, pas de graphiques ni actions | Partiel | `src/pages/DashboardPage.tsx` |
| Cimetières | Lister les cimetières | Page stub sans données ni actions | Non | `src/pages/CemeteriesPage.tsx` |
| Cimetières | Créer / modifier / supprimer un cimetière | Aucun formulaire ni bouton branché | Non | `src/pages/CemeteriesPage.tsx`, `src/hooks/useCemeteries.ts` |
| Emplacements | Voir le plan d'un cimetière réel | Carte basée sur `mockCemeteryMap`, pas sur SQLite | Non | `src/pages/EmplacementsPage.tsx`, `src/mocks/cemetery-map.ts` |
| Emplacements | Sélectionner un emplacement | Sélection possible sur données mockées | Partiel | `src/components/map/CemeteryMap.tsx`, `src/pages/EmplacementsPage.tsx` |
| Emplacements | Créer / modifier un emplacement | Aucun écran d'édition | Non | `src/pages/EmplacementsPage.tsx`, `src/hooks/usePlots.ts` |
| Concessions | Lister les concessions | Tableau affiché, filtres de statut présents | Oui en lecture | `src/pages/ConcessionsPage.tsx`, `src/hooks/useConcessions.ts` |
| Concessions | Ouvrir une fiche concession | Bouton `Détails` navigue vers la fiche | Oui en lecture | `src/pages/ConcessionsPage.tsx`, `src/pages/ConcessionDetailPage.tsx` |
| Concessions | Créer une concession | Backend existe mais aucune UI de saisie | Non | `src/hooks/useConcessions.ts`, `src/lib/tauri.ts`, `src/pages/ConcessionsPage.tsx` |
| Concessions | Modifier / renouveler / archiver / supprimer | Boutons visibles mais non branchés | Non | `src/pages/ConcessionDetailPage.tsx` |
| Concessions | Voir l'emplacement lié | Mini `PlotViewer` affiché si `plot_id` existe | Oui en lecture partielle | `src/pages/ConcessionDetailPage.tsx`, `src/components/map/PlotViewer.tsx` |
| Défunts | Lister les défunts | Liste filtrée sur `role === deceased` | Oui en lecture | `src/pages/DefuntsPage.tsx` |
| Défunts | Ouvrir la fiche depuis la liste | Bouton `Détails` sans navigation | Non | `src/pages/DefuntsPage.tsx` |
| Défunts | Ouvrir la fiche par URL directe | Route et page existent | Oui, seulement en accès direct | `src/router.tsx`, `src/pages/DefuntDetailPage.tsx` |
| Personnes | Gérer concessionnaires / ayants droit | Pas de liste dédiée, pas de formulaires, données réduites au strict minimum | Non | `SPEC.md` sections 5.5/8.2, `src/types/bindings.ts`, `src/pages/DefuntsPage.tsx` |
| Inhumations | Associer un défunt à une concession | Commande backend existante, aucune UI | Non | `src/hooks/useBurials.ts`, `src-tauri/src/commands/burial.rs` |
| Opérations funéraires | Agenda / planning / autorisations | Aucun écran | Non | `SPEC.md` section 5.7, `src/router.tsx` |
| Recherche | Chercher une personne | Formulaire fonctionnel pour une première recherche | Oui, limité | `src/pages/RecherchePage.tsx`, `src/hooks/useIndividuals.ts` |
| Recherche | Chercher une concession par ID | Fonctionne par ID numérique | Oui, limité | `src/pages/RecherchePage.tsx` |
| Recherche | Refaire plusieurs recherches successives | Hook `useQuery` ne dépend pas de la requête, risque de résultats figés | Non fiable | `src/hooks/useQuery.ts`, `src/pages/RecherchePage.tsx` |
| Recherche | Ouvrir un résultat depuis `Voir` | Boutons `Voir` non branchés | Non | `src/pages/RecherchePage.tsx` |
| Alertes | Voir les alertes existantes | Tableau et widget présents | Oui si données déjà calculées | `src/components/alerts/AlertsTable.tsx`, `src/components/alerts/AlertWidget.tsx` |
| Alertes | Générer / rafraîchir les alertes depuis l'UI | Aucune page n'appelle `refresh_alerts` | Non | `src/hooks/useAlerts.ts`, `src/pages/DashboardPage.tsx`, `src/pages/AlertesPage.tsx` |
| Alertes | Acquitter une alerte | Bouton branché | Oui | `src/components/alerts/AlertsTable.tsx`, `src/pages/ConcessionDetailPage.tsx` |
| PDF | Générer un PDF de fiche concession | Bouton branché, chemin retourné affiché | Oui, document simple | `src/hooks/usePdfGeneration.ts`, `src/pages/ConcessionDetailPage.tsx`, `src-tauri/src/services/pdf_service.rs` |
| PDF | Générer les documents administratifs du cahier des charges | Une seule fiche concession simple, sans modèles ni historique | Non | `SPEC.md` section 5.10, `src-tauri/src/commands/pdf.rs` |
| Sauvegardes | Créer une sauvegarde | Bouton branché mais contrat UI/back incohérent après création | Partiel et fragile | `src/pages/SauvegardesPage.tsx`, `src/hooks/useBackups.ts`, `src-tauri/src/commands/backup.rs` |
| Sauvegardes | Lister les sauvegardes | Backend renvoie `Vec<String>`, frontend attend des objets détaillés | Non | `src/hooks/useBackups.ts`, `src-tauri/src/commands/backup.rs`, `src-tauri/src/services/backup_service.rs` |
| Sauvegardes | Restaurer une sauvegarde | Frontend envoie `{ filename }`, backend attend `backup_filename` | Non | `src/hooks/useBackups.ts`, `src-tauri/src/commands/backup.rs` |
| Paramètres | Paramétrage communal | Page placeholder | Non | `src/pages/ParametresPage.tsx` |
| Utilisateurs / droits | Gérer des rôles | Aucun module | Non | `SPEC.md` section 5.19, `src/router.tsx` |
| Journal d'audit | Voir la traçabilité | Aucun module | Non | `SPEC.md` section 5.20, schéma SQLite actuel |
| Import | Import CSV / Excel | Aucun module | Non | `SPEC.md` section 5.17, `src/router.tsx` |
| Documents | Associer et consulter des pièces | Aucun module | Non | `SPEC.md` section 5.9, schéma SQLite actuel |
| Packaging | Installer et lancer une build municipale validée | Rapports contradictoires ; artefacts finaux non prouvés | Non prouvé | `reports/release/pilot_v0.1_artifacts_report.md`, `reports/release/pilot_v0.1_release_status_final.md`, `reports/release/pilot_v0.1_release_validation.md` |

## Lecture métier synthétique

Si une mairie reçoit aujourd'hui l'application packagée, elle peut surtout consulter des données déjà présentes, tester une carte de démonstration, voir quelques alertes et générer un PDF simple.

Elle ne peut pas gérer réellement un cimetière de bout en bout sans terminal, car les parcours de saisie, d'association, de maintenance des données et de restauration ne sont pas opérationnels en UI.
