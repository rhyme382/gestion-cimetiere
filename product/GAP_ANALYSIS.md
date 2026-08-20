# Gap Analysis

Date d'audit : 2026-07-11

## Resume executif

L'ecart a combler n'est pas seulement un ecart d'interface. C'est un ecart de produit : modele de donnees, regles metier, procedures administratives, securite locale, preuves de packaging et accompagnement utilisateur restent loin de la cible de `SPEC.md`.

Le depot actuel fournit un socle utile pour entrer en alpha, mais il ne couvre qu une partie restreinte du logiciel municipal final :
- schema SQLite limite a 6 tables metier et 1 table alertes ;
- parcours packagés majoritairement lecture seule ;
- cartographie de consultation branchee sur des mocks ;
- sauvegarde/restauration non fiable en UI ;
- absence de modules entiers : ayants droit, exhumations, urnes, reprises, tarifs, pieces, roles, audit, import, RGPD, aide embarquee.

## Modele domaine cible

Le cahier des charges final implique au minimum les agregats et relations suivants :

- `Municipality` : identité communale, coordonnées, logo, paramètres globaux, mentions RGPD.
- `Cemetery` : un ou plusieurs cimetières rattachés à une commune, avec règlement, horaires, plans et documents.
- `SpatialUnit` : section, carre, rangée, emplacement, niche, cavurne, ossuaire, jardin du souvenir, géométrie éventuelle.
- `Concession` : numéro, type, durée, dates, état, emplacement, produits tarifaires, paiements, alertes et procédure de reprise.
- `Person` : titulaire, cotitulaire, concessionnaire, ayant droit, héritier, contact, avec liens familiaux et historiques d adresse.
- `DeceasedRecord` : identité complète, décès, famille, entreprise funéraire, actes, photographie, rattachements.
- `FuneralOperation` : inhumation, exhumation, réduction, réunion, dépôt d urne, retrait, dispersion, transfert, ouverture/fermeture, travaux.
- `Document` et `Template` : documents générés, modèles, variables, publipostages, numérotation, historique.
- `Tariff`, `Invoice`, `Payment` : grilles, délibérations, encaissement, reste à payer, reçu.
- `Attachment` : scans, actes, courriers, photos, arrêtés, preuves.
- `Alert` : échéances, dossiers incomplets, seuils réglementaires, tâches à faire.
- `ImportBatch` : staging, mapping, validation, rollback.
- `User`, `Role`, `Permission`, `AuditEvent` : sécurité locale, journalisation et responsabilités.
- `BackupRecord` : sauvegarde, contrôle d intégrité, restauration, bundle de support.

## Ecarts structurants

### G1. Le produit actuel ne sait pas initialiser une exploitation metier complete
- Les parcours de création de cimetière, emplacement, concession, titulaire et défunt ne sont pas tous disponibles en UI packagée.
- Sans ces parcours, une mairie ne peut pas démarrer sur une base vide.

### G2. Le modele de donnees actuel est insuffisant pour le logiciel cible
- Pas de tables ou contrats pour ayants droit, pièces, tarifs, paiements, procédures, utilisateurs, audit, imports, RGPD.
- Les DTO actuels réduisent les personnes à `name/email/phone/role`, très loin des besoins civils et successoraux décrits dans `SPEC.md`.

### G3. Les dependances produit doivent repartir des contrats backend vers les UI
- Le second backlog corrige explicitement la logique d enchainement : modèle -> persistance -> commandes -> interface -> preuves QA.
- Les liens concession/personnes et les mouvements funéraires ne doivent plus être planifiés en UI avant que les capacités backend existent. Cette correction couvre notamment l inversion logique relevée autour d `ALPHA-014` dans le backlog de remise en état.

### G4. La cartographie doit devenir un module metier, pas une demo
- Le plan actuel ne lit pas SQLite et ne localise pas réellement concessions ni défunts.
- Le produit cible exige deux couches distinctes : consultation réelle puis édition géométrique versionnée.

### G5. Les procedures administratives et documentaires sont presque absentes
- Le PDF actuel est utile comme preuve de faisabilité, mais il ne remplace pas titres, courriers, arrêtés, avis d échéance, procès-verbaux, autorisations ni historique documentaire.

### G6. La securite locale et la tracabilite ne sont pas commencées
- Aucun rôle, aucun cloisonnement par profil, aucun journal d audit, aucune preuve RGPD embarquée.

### G7. Le packaging prouve moins que ce qu annoncent plusieurs rapports
- Le backend compile et les tests Rust passent.
- La suite frontend échoue actuellement (`@testing-library/dom` manquant).
- Les preuves de runs Playwright et d installateurs réellement validés restent partielles ou contradictoires selon les rapports lus.

## Ecarts par domaine

### Referentiel communal et cimetieres
- Etat observe : Page Cimetières placeholder, pas de CRUD packagé.
- Cap cible : Multi-cimetières, identité communale, horaires, règlement, plans, notes et photos.
- Taches backlog : FP-001 Modeler le referentiel communal et les fiches cimetieres, FP-002 Livrer le parcours UI de creation et modification des cimetieres, FP-003 Gerer les metadonnees de cimetiere

### Sections, carres, rangees et emplacements
- Etat observe : Structure réduite aux plots simples ; pas de gestion UI réelle.
- Cap cible : Maillage spatial complet, capacités, statuts et disponibilité exploitable.
- Taches backlog : FP-004 Modeler la hierarchie sections carres rangees et emplacements, FP-005 Implementer le CRUD backend des emplacements et leurs statuts, FP-006 Livrer l interface de gestion des emplacements

### Columbariums, cavurnes, ossuaires et jardins du souvenir
- Etat observe : Aucun support métier distinct hors type théorique dans SPEC.
- Cap cible : Gestion distincte des espaces cinéraires et mémoriels.
- Taches backlog : FP-007 Etendre le modele des emplacements aux espaces cineraires et memoriels, FP-008 Gerer modules niches cases et capacites des espaces cineraires, FP-009 Livrer les parcours UI des espaces cineraires et du jardin du souvenir

### Concessions
- Etat observe : Lecture partielle seulement ; creation et edition non branchées.
- Cap cible : Cycle de vie complet : création, renouvellement, conversion, clôture, archive.
- Taches backlog : FP-010 Modeler le contrat de concession et son cycle de vie, FP-011 Implementer les workflows backend de creation modification renouvellement et archivage des concessions, FP-012 Livrer la gestion UI complete des concessions

### Titulaires, cotitulaires et concessionnaires
- Etat observe : Personnes réduites à name/email/phone/role sans lien riche.
- Cap cible : Rôles juridiques différenciés et historisés.
- Taches backlog : FP-013 Modeler les roles de titulaire cotitulaire et concessionnaire, FP-014 Associer les titulaires et cotitulaires aux concessions avec dates d effet, FP-015 Livrer la gestion UI des titulaires depuis la fiche concession

### Ayants droit, heritiers et liens familiaux
- Etat observe : Absent.
- Cap cible : Réseau familial, preuves et statuts successoraux.
- Taches backlog : FP-016 Modeler les ayants droit heritiers et liens familiaux, FP-017 Tracer justificatifs et statuts de succession des ayants droit, FP-018 Livrer l interface de gestion des ayants droit et de leurs liens

### Defunts
- Etat observe : Lecture partielle ; creation et navigation incomplètes.
- Cap cible : Identité civile complète, décès, rattachements et historique.
- Taches backlog : FP-019 Modeler l identite civile complete des defunts, FP-020 Implementer les workflows backend de creation mise a jour et consultation des defunts, FP-021 Livrer la creation et la navigation UI des fiches defunts

### Inhumations
- Etat observe : Commande minimale existante sans parcours UI complet.
- Cap cible : Enregistrement réglementé avec contrôles de capacité et autorisations.
- Taches backlog : FP-022 Modeler l inhumation avec autorisations et controles de capacite, FP-023 Renforcer le workflow backend qui lie defunt concession et emplacement, FP-024 Livrer l enregistrement UI des inhumations

### Exhumations
- Etat observe : Absent.
- Cap cible : Demande, autorisation, exécution et destination.
- Taches backlog : FP-025 Modeler la demande d exhumation et ses autorisations, FP-026 Implementer le workflow backend d exhumation et son historique, FP-027 Livrer l interface de gestion des exhumations

### Reductions et reunions de corps
- Etat observe : Absent.
- Cap cible : Opérations distinctes avec traçabilité des restes.
- Taches backlog : FP-028 Modeler les reductions et reunions de corps, FP-029 Appliquer les regles de capacite et de chaine de conservation des restes, FP-030 Livrer l interface de reduction et reunion de corps

### Urnes, depots, retraits et dispersions
- Etat observe : Absent.
- Cap cible : Cycle complet des urnes et dispersions.
- Taches backlog : FP-031 Modeler les urnes et leurs etats de conservation, FP-032 Implementer les workflows de depot retrait et dispersion des urnes, FP-033 Livrer l interface de gestion des urnes et dispersions

### Transferts et mouvements funeraires
- Etat observe : Absent.
- Cap cible : Journal unifié des mouvements de corps et d urnes.
- Taches backlog : FP-034 Modeler un journal unifie des mouvements funeraires, FP-035 Implementer les transferts entre emplacements et cimetières, FP-036 Livrer la consultation UI de l historique des mouvements

### Cartographie de consultation
- Etat observe : Carte mockée, non connectée à SQLite.
- Cap cible : Localisation réelle des emplacements, concessions et défunts.
- Taches backlog : FP-037 Exposer des donnees cartographiques reelles depuis SQLite, FP-038 Connecter la carte de consultation aux donnees reelles, FP-039 Permettre la localisation depuis la recherche et les fiches

### Cartographie editable
- Etat observe : Absent.
- Cap cible : Edition des géométries, publication et versioning des plans.
- Taches backlog : FP-040 Modeler les geometries editables et les versions de plan, FP-041 Construire les outils de dessin et d affectation des polygones, FP-042 Publier les modifications de plan via un workflow de validation

### Echeances et renouvellements
- Etat observe : Alertes partielles ; renouvellement UI absent.
- Cap cible : Calcul d échéance, relances, renouvellements et états.
- Taches backlog : FP-043 Implementer le moteur de calcul des echeances par type et duree, FP-044 Implementer le workflow de renouvellement avec nouveau terme et redevance, FP-045 Livrer le tableau de bord des echeances et les actions UI de renouvellement

### Procedures d abandon et de reprise
- Etat observe : Absent.
- Cap cible : Dossier réglementaire complet avec délais et arrêtés.
- Taches backlog : FP-046 Modeler le dossier de procedure d abandon et de reprise, FP-047 Suivre les constats affichages courriers et arretes de reprise, FP-048 Livrer l interface de suivi des procedures de reprise

### Documents administratifs
- Etat observe : Un seul PDF simple de fiche concession.
- Cap cible : Catalogue des documents municipaux générés depuis les dossiers.
- Taches backlog : FP-049 Definir le catalogue des documents administratifs et leurs contrats de donnees, FP-050 Generer les documents administratifs prioritaires, FP-051 Livrer les actions UI de generation documentaire depuis les dossiers

### Modeles, publipostage et historique documentaire
- Etat observe : Absent.
- Cap cible : Modèles, fusion en lot, numérotation et historique.
- Taches backlog : FP-052 Gerer les modeles de documents et les variables de fusion, FP-053 Implementer les lots de publipostage et l historique des courriers, FP-054 Livrer l interface de previsualisation des modeles et historiques documentaires

### Tarifs, redevances et paiements
- Etat observe : Absent.
- Cap cible : Grilles tarifaires, encaissement, impayés et reçus.
- Taches backlog : FP-055 Modeler les grilles tarifaires et les produits de concession, FP-056 Enregistrer les paiements et etats de redevance des dossiers, FP-057 Livrer l interface tarifs et paiements

### Recherche multicritere et doublons
- Etat observe : Recherche simple fragile, ouverture résultats incomplète.
- Cap cible : Recherche transversale, ouverture des résultats, détection de doublons.
- Taches backlog : FP-058 Construire une recherche globale multicritere indexee, FP-059 Detecter les doublons et assister la fusion de fiches, FP-060 Livrer une UI de recherche fiable avec ouverture des resultats

### Tableaux de bord, statistiques et editions
- Etat observe : Dashboard partiel, compteurs incomplets.
- Cap cible : KPI métier, éditions imprimables et analyses par période.
- Taches backlog : FP-061 Definir les indicateurs de pilotage et agregats statistiques, FP-062 Livrer le dashboard metier et les editions imprimables minimales, FP-063 Ajouter les statistiques avancees et editions analytiques

### Import CSV/Excel et reprise de donnees
- Etat observe : Absent.
- Cap cible : Assistant d import, staging, validation, rollback.
- Taches backlog : FP-064 Modeler les lots d import et les tables de staging, FP-065 Construire le moteur d import CSV Excel avec rapport de validation, FP-066 Livrer l assistant UI de reprise de donnees

### Documents joints et photographies
- Etat observe : Absent.
- Cap cible : Pièces attachées, prévisualisation et sauvegarde avec la base.
- Taches backlog : FP-067 Modeler le stockage des documents joints et photographies, FP-068 Implementer le televersement l apercu et la restitution des pieces, FP-069 Livrer l interface de consultation et classement des pieces

### Utilisateurs, roles et habilitations
- Etat observe : Absent.
- Cap cible : Profils locaux, restrictions d actions et administration.
- Taches backlog : FP-070 Modeler les utilisateurs locaux roles et sessions, FP-071 Appliquer les controles d acces sur les commandes et ecrans, FP-072 Livrer l administration UI des utilisateurs et roles

### Journal d audit et tracabilite
- Etat observe : Absent.
- Cap cible : Traçabilité immuable des actions et exports.
- Taches backlog : FP-073 Modeler un journal d audit immuable, FP-074 Capturer automatiquement les traces depuis les commandes backend, FP-075 Livrer l interface de consultation du journal d audit

### Sauvegarde, restauration et integrite
- Etat observe : Backend existant mais contrat UI cassé et stockage à fiabiliser.
- Cap cible : Sauvegarde locale fiable, restauration validée, preuves d intégrité.
- Taches backlog : FP-076 Migrer la base et les sauvegardes vers des repertoires applicatifs OS avec metadonnees d integrite, FP-077 Corriger et completer le workflow backend de restauration, FP-078 Livrer une UI de sauvegarde restauration et preuves d integrite

### Parametrage communal
- Etat observe : Page Paramètres placeholder.
- Cap cible : Identité de la commune, durées, alertes, types, couleurs et modèles.
- Taches backlog : FP-079 Modeler les parametres communaux de base, FP-080 Livrer l interface de parametrage communal, FP-081 Propager les parametres aux alertes documents et legende cartographique

### Packaging, installation et mises a jour
- Etat observe : Configuration présente, usage final packagé non prouvé.
- Cap cible : Installateurs prouvés, premier démarrage guidé, upgrade maîtrisé.
- Taches backlog : FP-082 Produire des installateurs et un premier demarrage metier guides, FP-083 Implementer le workflow de mise a jour applicative et de migration de donnees, FP-084 Valider en QA les parcours d installation lancement et upgrade Windows Linux

### RGPD, export et conservation
- Etat observe : Absent.
- Cap cible : Politiques de conservation, export, archivage, anonymisation.
- Taches backlog : FP-085 Modeler les politiques de retention et les bases legales, FP-086 Construire les exports les archives controlees et l anonymisation, FP-087 Livrer l interface RGPD et les preuves de traitement

### Aide, documentation et accompagnement utilisateur
- Etat observe : Documentation technique présente, aide embarquée absente.
- Cap cible : Aide embarquée, onboarding et bundle de support.
- Taches backlog : FP-088 Produire un centre d aide role par role et une documentation contextuelle, FP-089 Construire un onboarding guide et des jeux de donnees de demonstration, FP-090 Exporter un bundle de support et un assistant de diagnostic

## Conclusion

Le premier audit alpha doit rester la reference pour reparer l'existant immediate. Le second audit montre cependant qu une alpha exploitable n est qu une etape dans un chantier produit beaucoup plus large : atteindre un logiciel municipal complet, sécurisé, réglementaire, documenté et réellement utilisable depuis une build packagée.