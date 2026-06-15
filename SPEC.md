# Cahier des charges complet — Logiciel de gestion de cimetières pour mairies

## 1. Vision du projet

Le projet consiste à développer un logiciel professionnel de gestion de cimetières destiné aux mairies, communes rurales, communes moyennes et services funéraires municipaux.

L’objectif est de proposer une solution moderne, esthétique, ergonomique et complète, comparable visuellement aux meilleures interfaces du marché, tout en intégrant les meilleures fonctionnalités observées dans les logiciels spécialisés existants : Gescime, Requiem, e.Cimetière, Cimetiere.services, Gestion-du-cimetière.fr, OpenCimetière et solutions SIG associées.

Le logiciel devra être installable comme une application autonome multiplateforme, compatible Windows et Linux. Sous Windows, l’installation devra passer par un installateur graphique propre, professionnel et simple pour une mairie non technicienne.

Le projet sera développé par plusieurs agents IA coordonnés :

- IA chef d’orchestre : Codex CLI
- IA de développement : Claude Code, plusieurs instances spécialisées
- IA de validation et tests : Codex CLI séparé

Le cahier des charges doit permettre à ces agents de travailler de façon autonome, coordonnée, testable et documentée.

---

## 2. Public cible

Le logiciel vise principalement :

- les petites communes ;
- les communes rurales ;
- les communes de 1 000 à 10 000 habitants ;
- les services état civil / population ;
- les secrétaires de mairie ;
- les élus chargés du cimetière ;
- les agents techniques intervenant sur le terrain ;
- les communes souhaitant moderniser des registres papier ou Excel.

---

## 3. Objectifs principaux

Le logiciel doit permettre :

1. De gérer toutes les concessions d’un ou plusieurs cimetières municipaux.
2. De gérer les défunts, ayants droit, concessionnaires et contacts familiaux.
3. De visualiser le cimetière sur une cartographie claire, interactive et esthétique.
4. De suivre les échéances, renouvellements, abandons et reprises de concessions.
5. De générer les documents administratifs nécessaires.
6. De produire des statistiques fiables pour la commune.
7. De faciliter les recherches par les familles, les agents et les élus.
8. De proposer une interface moderne, fluide, agréable et intuitive.
9. De fonctionner hors ligne, sans dépendre obligatoirement d’un serveur externe.
10. De permettre une installation autonome sous Windows et Linux.

---

## 4. Principes de conception

### 4.1 Simplicité pour la mairie

Le logiciel doit être compréhensible par une secrétaire de mairie non informaticienne.

L’interface doit être claire, avec des termes métiers :

- concession ;
- emplacement ;
- concessionnaire ;
- défunt ;
- ayant droit ;
- renouvellement ;
- reprise ;
- columbarium ;
- cavurne ;
- ossuaire ;
- terrain commun ;
- concession échue ;
- concession abandonnée.

### 4.2 Esthétique professionnelle

L’interface doit être aussi belle que les meilleurs SaaS modernes :

- design clair ;
- typographie lisible ;
- cartes synthétiques ;
- tableaux modernes ;
- filtres rapides ;
- icônes sobres ;
- code couleur intelligent ;
- cartographie fluide ;
- mode clair et mode sombre si possible.

### 4.3 Robustesse administrative

Le logiciel doit respecter les usages des communes françaises et produire des documents exploitables juridiquement.

### 4.4 Fonctionnement local prioritaire

Le logiciel doit pouvoir tourner localement sans serveur distant, avec une base de données embarquée.

### 4.5 Évolutivité

L’architecture doit permettre ensuite :

- une version réseau ;
- une version SaaS ;
- un portail public ;
- une synchronisation cloud ;
- une application mobile terrain ;
- une intégration SIG avancée.

---

## 5. Modules fonctionnels

## 5.1 Tableau de bord général

Le tableau de bord doit afficher :

- nombre total de concessions ;
- concessions occupées ;
- concessions libres ;
- concessions arrivant à échéance ;
- concessions échues ;
- concessions en procédure de reprise ;
- emplacements disponibles ;
- nombre de défunts enregistrés ;
- alertes prioritaires ;
- tâches à faire ;
- opérations funéraires à venir ;
- statistiques rapides.

Fonctionnalités attendues :

- cartes de synthèse ;
- graphiques ;
- raccourcis vers les actions fréquentes ;
- recherche globale ;
- filtres rapides ;
- export PDF du tableau de bord.

---

## 5.2 Gestion des cimetières

Le logiciel doit gérer plusieurs cimetières pour une même commune.

Pour chaque cimetière :

- nom ;
- adresse ;
- description ;
- surface ;
- nombre d’emplacements ;
- secteurs ;
- carrés ;
- rangées ;
- plans ;
- photos ;
- règlement intérieur ;
- horaires ;
- notes internes.

---

## 5.3 Gestion des emplacements

Chaque emplacement doit pouvoir être décrit précisément :

- identifiant unique ;
- cimetière ;
- secteur ;
- carré ;
- rangée ;
- numéro ;
- type : pleine terre, caveau, columbarium, cavurne, ossuaire, jardin du souvenir, terrain commun ;
- coordonnées sur le plan ;
- surface approximative ;
- capacité théorique ;
- capacité restante ;
- état : libre, occupé, réservé, abandonné, en reprise, indisponible ;
- photos ;
- observations ;
- historique des modifications.

---

## 5.4 Gestion des concessions

Fonctionnalités :

- création d’une concession ;
- modification ;
- renouvellement ;
- conversion ;
- reprise ;
- abandon ;
- clôture ;
- archivage ;
- transfert éventuel ;
- rattachement à un emplacement ;
- rattachement à un concessionnaire ;
- rattachement aux ayants droit ;
- rattachement aux défunts.

Données à gérer :

- numéro de concession ;
- type de concession ;
- durée : 15 ans, 30 ans, 50 ans, perpétuelle, autre ;
- date d’achat ;
- date de début ;
- date de fin ;
- prix ;
- mode de paiement ;
- titre de concession ;
- acte associé ;
- concessionnaire initial ;
- concessionnaire actuel ;
- ayants droit ;
- défunts inhumés ;
- documents liés ;
- état administratif ;
- observations.

Statuts possibles :

- active ;
- bientôt échue ;
- échue ;
- renouvelée ;
- abandonnée ;
- procédure de reprise en cours ;
- reprise ;
- archivée.

---

## 5.5 Gestion des concessionnaires et ayants droit

Pour chaque personne :

- nom ;
- prénom ;
- nom de naissance ;
- date de naissance ;
- lieu de naissance ;
- adresse ;
- téléphone ;
- email ;
- qualité : concessionnaire, ayant droit, contact famille, mandataire ;
- lien avec le défunt ;
- lien avec la concession ;
- pièces justificatives ;
- notes ;
- historique des courriers envoyés.

Fonctionnalités :

- recherche de doublons ;
- fusion de fiches ;
- historique des adresses ;
- export CSV ;
- génération de courriers personnalisés.

---

## 5.6 Gestion des défunts

Pour chaque défunt :

- nom ;
- prénom ;
- nom de naissance ;
- sexe ;
- date de naissance ;
- lieu de naissance ;
- date de décès ;
- lieu de décès ;
- date d’inhumation ;
- type d’inhumation ;
- emplacement ;
- concession associée ;
- famille ;
- entreprise funéraire ;
- acte de décès ;
- observations ;
- photo de sépulture si disponible.

Fonctionnalités :

- recherche multicritère ;
- fiche défunt ;
- historique des opérations ;
- export d’une fiche ;
- lien vers la cartographie ;
- recherche phonétique approximative.

---

## 5.7 Gestion des opérations funéraires

Le logiciel doit gérer :

- inhumation ;
- exhumation ;
- réduction de corps ;
- dépôt d’urne ;
- dispersion des cendres ;
- transfert ;
- ouverture de caveau ;
- fermeture de caveau ;
- travaux marbriers ;
- intervention d’entreprise ;
- passage en ossuaire.

Données :

- date ;
- heure ;
- type d’opération ;
- défunt concerné ;
- concession concernée ;
- entreprise funéraire ;
- autorisation ;
- agent municipal ;
- observations ;
- documents associés.

Fonctionnalités :

- agenda ;
- planning hebdomadaire ;
- notifications ;
- export PDF ;
- édition des autorisations.

---

## 5.8 Cartographie interactive

Module central du logiciel.

Fonctionnalités :

- plan interactif du cimetière ;
- zoom ;
- déplacement ;
- sélection d’un emplacement ;
- coloration selon le statut ;
- affichage rapide d’une fiche ;
- recherche directe sur le plan ;
- filtres visuels ;
- localisation d’un défunt ;
- localisation d’une concession ;
- affichage des emplacements libres ;
- affichage des concessions échues ;
- impression du plan ;
- export image/PDF ;
- import d’un plan image ;
- dessin manuel de polygones ;
- rattachement d’un polygone à un emplacement ;
- possibilité future d’import SIG.

Codes couleur suggérés :

- vert : libre ;
- bleu : occupé ;
- orange : bientôt échu ;
- rouge : échu ;
- violet : reprise en cours ;
- gris : indisponible ;
- noir : ossuaire ou espace spécial.

---

## 5.9 Gestion documentaire

Le logiciel doit permettre d’associer des documents :

- titre de concession ;
- acte de décès ;
- courrier ;
- autorisation d’inhumation ;
- autorisation d’exhumation ;
- justificatif d’identité ;
- règlement ;
- photo ;
- scan ancien registre ;
- délibération tarifaire ;
- arrêté municipal.

Fonctionnalités :

- import PDF ;
- import image ;
- classement par type ;
- aperçu intégré ;
- ouverture externe ;
- export ;
- stockage local structuré ;
- indexation minimale ;
- future OCR possible.

---

## 5.10 Génération de documents administratifs

Le logiciel doit générer :

- titre de concession ;
- renouvellement de concession ;
- avis d’échéance ;
- relance ;
- courrier aux ayants droit ;
- procès-verbal de constat d’abandon ;
- courrier de procédure de reprise ;
- arrêté municipal ;
- autorisation d’inhumation ;
- autorisation d’exhumation ;
- autorisation de travaux ;
- registre d’inhumation ;
- registre d’exhumation ;
- fiche concession ;
- fiche défunt ;
- reçu ou état des paiements.

Fonctionnalités :

- modèles personnalisables ;
- variables automatiques ;
- export PDF ;
- export DOCX si possible ;
- historique des documents générés ;
- numérotation automatique.

---

## 5.11 Alertes et échéances

Alertes attendues :

- concession arrivant à échéance dans 6 mois ;
- concession échue ;
- procédure de reprise à lancer ;
- courrier à envoyer ;
- opération funéraire prévue ;
- dossier incomplet ;
- document manquant ;
- concession sans ayant droit connu ;
- emplacement incohérent ;
- capacité dépassée.

Fonctionnalités :

- centre de notifications ;
- filtres ;
- tâches ;
- statut : à faire, en cours, terminé, ignoré ;
- rappel ;
- export liste d’alertes.

---

## 5.12 Procédure de reprise des concessions abandonnées

Le logiciel doit accompagner la commune dans la procédure.

Étapes à modéliser :

1. Identification de la concession potentiellement abandonnée.
2. Constat sur place.
3. Rédaction du procès-verbal.
4. Information des ayants droit si connus.
5. Affichage réglementaire.
6. Suivi des délais.
7. Nouveau constat si nécessaire.
8. Décision municipale.
9. Arrêté de reprise.
10. Archivage du dossier.

Chaque étape doit contenir :

- date ;
- responsable ;
- document associé ;
- commentaire ;
- état ;
- alerte de délai.

---

## 5.13 Statistiques et rapports

Rapports attendus :

- taux d’occupation ;
- concessions libres ;
- concessions échues ;
- concessions à renouveler ;
- concessions par durée ;
- concessions par type ;
- nombre annuel d’inhumations ;
- nombre annuel d’exhumations ;
- disponibilité prévisionnelle ;
- recettes liées aux concessions ;
- emplacements disponibles par secteur ;
- état du columbarium ;
- concessions sans contact familial.

Exports :

- PDF ;
- CSV ;
- Excel si possible ;
- impression.

---

## 5.14 Recherche globale

Recherche dans :

- défunts ;
- concessions ;
- concessionnaires ;
- ayants droit ;
- emplacements ;
- documents ;
- opérations.

Fonctionnalités :

- recherche rapide ;
- filtres avancés ;
- tri ;
- recherche approximative ;
- recherche par année ;
- recherche par emplacement ;
- recherche par famille.

---

## 5.15 Portail public optionnel

Version future ou module optionnel.

Fonctionnalités possibles :

- recherche publique d’un défunt ;
- affichage limité des informations ;
- plan simplifié ;
- itinéraire vers la tombe ;
- QR code sur plan ou sépulture ;
- respect RGPD ;
- désactivation complète possible.

Ce module ne doit pas être obligatoire pour la première version locale.

---

## 5.16 QR codes

Fonctionnalités :

- génération de QR code pour un emplacement ;
- génération de QR code pour un défunt ;
- impression d’étiquettes ;
- lien vers fiche interne ;
- lien futur vers portail public ;
- mode privé/public configurable.

---

## 5.17 Import de données

Le logiciel doit importer :

- fichiers CSV ;
- fichiers Excel ;
- listes de concessions ;
- listes de défunts ;
- listes d’ayants droit ;
- anciens exports logiciels ;
- données issues d’un registre papier saisi manuellement.

Fonctionnalités :

- assistant d’import ;
- mapping des colonnes ;
- prévisualisation ;
- détection d’erreurs ;
- rapport d’import ;
- possibilité d’annuler un import.

---

## 5.18 Export et sauvegarde

Exports :

- CSV ;
- JSON ;
- PDF ;
- ZIP complet ;
- sauvegarde de base de données ;
- sauvegarde documents associés.

Sauvegarde :

- sauvegarde manuelle ;
- sauvegarde automatique locale ;
- choix du dossier ;
- restauration ;
- vérification d’intégrité ;
- journal des sauvegardes.

---

## 5.19 Gestion des utilisateurs et droits

Même pour une version locale, prévoir :

- administrateur ;
- secrétaire de mairie ;
- agent technique ;
- élu consultation ;
- lecture seule ;
- droits personnalisables.

Journaliser :

- créations ;
- modifications ;
- suppressions ;
- exports ;
- génération de documents ;
- changements de statut.

---

## 5.20 Journal d’audit

Le journal doit conserver :

- date ;
- utilisateur ;
- action ;
- entité concernée ;
- ancienne valeur ;
- nouvelle valeur ;
- commentaire éventuel.

Objectif : traçabilité administrative.

---

## 5.21 Paramétrage communal

Paramètres :

- nom de la commune ;
- logo ;
- adresse ;
- maire ;
- service référent ;
- tarifs des concessions ;
- durées disponibles ;
- modèles de documents ;
- couleurs du plan ;
- types d’emplacements ;
- délais d’alerte ;
- sauvegardes ;
- mentions RGPD.

---

## 5.22 Réglementation et RGPD

Le logiciel devra intégrer :

- minimisation des données ;
- droits d’accès ;
- journalisation ;
- export des données ;
- suppression ou archivage contrôlé ;
- mentions RGPD ;
- gestion des données sensibles avec prudence ;
- séparation des données publiques et privées ;
- possibilité de masquer certains champs sur le portail public.

---

# 6. Architecture technique recommandée

## 6.1 Choix principal recommandé

Architecture recommandée : application desktop multiplateforme avec Tauri.

Stack proposée :

- Frontend : React + TypeScript
- UI : Tailwind CSS + shadcn/ui
- Cartographie : Leaflet ou MapLibre GL selon besoin
- Backend local : Rust via Tauri commands
- Base de données : SQLite
- ORM/migrations : SQLx ou Prisma côté Node si architecture hybride
- Génération PDF : moteur HTML vers PDF ou bibliothèque Rust adaptée
- Documents : templates Markdown/HTML convertibles en PDF
- Packaging Windows : Tauri Bundler + NSIS
- Packaging Linux : AppImage + .deb si possible
- Tests frontend : Vitest + Testing Library
- Tests E2E : Playwright
- Tests backend : cargo test
- CI : GitHub Actions

Pourquoi Tauri :

- application légère ;
- bundle autonome ;
- très bon support Windows/Linux ;
- installateur Windows possible ;
- sécurité meilleure qu’Electron ;
- intégration Rust performante ;
- accès local au système de fichiers ;
- bonne compatibilité avec SQLite.

---

## 6.2 Alternative possible

Alternative : Electron + React + SQLite.

Avantages :

- écosystème très large ;
- packaging mature ;
- plus simple pour certains développeurs web.

Inconvénients :

- application plus lourde ;
- consommation mémoire plus importante ;
- moins élégante pour une distribution communale légère.

Décision recommandée : Tauri.

---

## 6.3 Structure du dépôt

```text
cimetiere-manager/
├── README.md
├── AGENTS.md
├── ROADMAP.md
├── CHANGELOG.md
├── docs/
│   ├── cahier_des_charges.md
│   ├── architecture.md
│   ├── database_schema.md
│   ├── ui_guidelines.md
│   ├── agent_workflow.md
│   ├── testing_strategy.md
│   └── legal_rgpd.md
├── apps/
│   └── desktop/
│       ├── src/
│       ├── src-tauri/
│       ├── package.json
│       ├── tauri.conf.json
│       └── vite.config.ts
├── packages/
│   ├── ui/
│   ├── domain/
│   ├── validators/
│   └── document-templates/
├── database/
│   ├── migrations/
│   ├── seeds/
│   └── schema.sql
├── tests/
│   ├── e2e/
│   ├── fixtures/
│   └── reports/
├── agents/
│   ├── orchestrator/
│   ├── dev-frontend/
│   ├── dev-backend/
│   ├── dev-database/
│   ├── dev-packaging/
│   ├── dev-documents/
│   └── validator/
├── tasks/
│   ├── backlog.md
│   ├── in_progress.md
│   ├── review.md
│   └── done.md
└── scripts/
    ├── setup.sh
    ├── setup.ps1
    ├── test_all.sh
    ├── build_windows.ps1
    └── build_linux.sh
```

---

# 7. Modèle de données principal

## 7.1 Entités principales

- Municipality
- Cemetery
- CemeterySection
- CemeteryRow
- Plot
- Concession
- Person
- Deceased
- BurialOperation
- Document
- DocumentTemplate
- Alert
- Task
- AuditLog
- User
- Role
- Setting
- ImportBatch
- BackupRecord

---

## 7.2 Tables minimales

### cemetery

- id
- name
- address
- description
- created_at
- updated_at

### plot

- id
- cemetery_id
- section
- row_label
- number
- type
- status
- capacity_total
- capacity_used
- map_x
- map_y
- polygon_json
- notes
- created_at
- updated_at

### concession

- id
- plot_id
- concession_number
- concession_type
- duration_years
- start_date
- end_date
- purchase_date
- price
- status
- owner_person_id
- notes
- created_at
- updated_at

### person

- id
- first_name
- last_name
- birth_name
- birth_date
- birth_place
- address
- phone
- email
- person_type
- notes
- created_at
- updated_at

### deceased

- id
- first_name
- last_name
- birth_name
- birth_date
- birth_place
- death_date
- death_place
- burial_date
- concession_id
- plot_id
- notes
- created_at
- updated_at

### burial_operation

- id
- type
- operation_date
- deceased_id
- concession_id
- plot_id
- funeral_company
- authorization_reference
- notes
- created_at
- updated_at

### document

- id
- entity_type
- entity_id
- document_type
- title
- file_path
- created_at
- updated_at

### alert

- id
- type
- severity
- entity_type
- entity_id
- message
- due_date
- status
- created_at
- updated_at

### audit_log

- id
- user_id
- action
- entity_type
- entity_id
- old_value_json
- new_value_json
- created_at

---

# 8. Interface utilisateur

## 8.1 Style visuel

L’interface doit être :

- moderne ;
- sobre ;
- institutionnelle ;
- claire ;
- rassurante ;
- élégante ;
- adaptée aux agents de mairie.

Palette suggérée :

- bleu profond pour l’administration ;
- vert doux pour les emplacements libres ;
- orange pour les alertes ;
- rouge sobre pour les échéances critiques ;
- gris clair pour les arrière-plans ;
- blanc cassé pour les cartes.

## 8.2 Écrans obligatoires

- écran d’accueil ;
- tableau de bord ;
- liste des cimetières ;
- plan interactif ;
- liste des concessions ;
- fiche concession ;
- liste des défunts ;
- fiche défunt ;
- liste des personnes ;
- agenda des opérations ;
- documents ;
- alertes ;
- statistiques ;
- import ;
- sauvegarde ;
- paramètres ;
- utilisateurs ;
- journal d’audit.

## 8.3 Composants UI

- sidebar principale ;
- barre de recherche globale ;
- tableaux filtrables ;
- badges de statut ;
- cartes statistiques ;
- modales de confirmation ;
- formulaires multi-onglets ;
- timeline historique ;
- visualiseur PDF/image ;
- assistant étape par étape ;
- notifications toast ;
- skeleton loading ;
- page d’erreur propre.

---

# 9. Packaging et installation

## 9.1 Windows

Objectif : installateur graphique propre.

Exigences :

- fichier `.exe` d’installation ;
- assistant graphique ;
- choix du dossier d’installation ;
- création raccourci bureau ;
- création raccourci menu démarrer ;
- désinstallation propre ;
- signature future possible ;
- base locale dans un dossier utilisateur ;
- sauvegardes dans un dossier configurable.

Technologie :

- Tauri Bundler avec NSIS.

## 9.2 Linux

Formats souhaités :

- AppImage ;
- paquet `.deb` si possible.

Exigences :

- lancement sans configuration complexe ;
- stockage local dans `~/.local/share/` ;
- raccourci bureau si installé via paquet ;
- script de diagnostic.

---

# 10. Sécurité

Mesures :

- base SQLite locale ;
- sauvegardes horodatées ;
- validation stricte des entrées ;
- pas d’exécution arbitraire ;
- journalisation des actions sensibles ;
- confirmations avant suppression ;
- droits utilisateurs ;
- export complet possible ;
- chiffrement futur possible de la base ou des sauvegardes.

---

# 11. Tests et validation

## 11.1 Tests obligatoires

- tests unitaires domaine ;
- tests base de données ;
- tests de migration ;
- tests composants UI ;
- tests E2E ;
- tests d’import CSV ;
- tests de génération PDF ;
- tests de sauvegarde/restauration ;
- tests packaging Windows ;
- tests packaging Linux.

## 11.2 Scénarios métier à tester

1. Créer un cimetière.
2. Créer un emplacement.
3. Créer une concession.
4. Ajouter un concessionnaire.
5. Ajouter un défunt.
6. Associer défunt, concession et emplacement.
7. Générer un titre de concession.
8. Déclencher une alerte d’échéance.
9. Renouveler une concession.
10. Lancer une procédure de reprise.
11. Importer un CSV de concessions.
12. Exporter un rapport PDF.
13. Sauvegarder la base.
14. Restaurer la base.
15. Rechercher un défunt depuis la barre globale.
16. Le localiser sur le plan.

---

# 12. Organisation multi-agents IA

## 12.1 Rôles

### Agent 1 — Chef d’orchestre Codex CLI

Responsabilités :

- créer le dépôt ;
- lire le cahier des charges ;
- découper le travail en lots ;
- créer les tickets dans `tasks/backlog.md` ;
- attribuer les lots aux agents Claude Code ;
- imposer les conventions ;
- vérifier les conflits ;
- intégrer les branches ;
- maintenir la roadmap ;
- demander validation à l’agent test.

### Agent 2 — Claude Code frontend

Responsabilités :

- interface React ;
- design system ;
- écrans ;
- composants ;
- formulaires ;
- cartographie ;
- expérience utilisateur.

### Agent 3 — Claude Code backend local

Responsabilités :

- commandes Tauri ;
- accès SQLite ;
- logique métier ;
- validation ;
- génération d’alertes ;
- sauvegarde/restauration.

### Agent 4 — Claude Code base de données

Responsabilités :

- modèle SQL ;
- migrations ;
- seeds ;
- fixtures ;
- import CSV ;
- cohérence des relations.

### Agent 5 — Claude Code documents

Responsabilités :

- modèles administratifs ;
- génération PDF ;
- variables ;
- aperçu ;
- stockage documentaire.

### Agent 6 — Claude Code packaging

Responsabilités :

- build Windows ;
- installateur NSIS ;
- AppImage ;
- .deb ;
- scripts de build ;
- documentation d’installation.

### Agent 7 — Codex CLI validation

Responsabilités :

- relire le code ;
- exécuter les tests ;
- détecter les régressions ;
- vérifier le respect du cahier des charges ;
- refuser les intégrations incomplètes ;
- produire un rapport de validation.

---

## 12.2 Communication entre agents

Les agents doivent communiquer exclusivement par fichiers dans le dépôt.

Fichiers de coordination :

```text
AGENTS.md
ROADMAP.md
tasks/backlog.md
tasks/in_progress.md
tasks/review.md
tasks/done.md
agents/orchestrator/log.md
agents/dev-frontend/log.md
agents/dev-backend/log.md
agents/dev-database/log.md
agents/dev-documents/log.md
agents/dev-packaging/log.md
agents/validator/log.md
```

Chaque agent doit :

1. Lire `AGENTS.md` avant toute action.
2. Lire `ROADMAP.md`.
3. Lire le ticket qui lui est attribué.
4. Écrire son plan dans son fichier `agents/.../log.md`.
5. Modifier uniquement les fichiers autorisés par le ticket.
6. Lancer les tests concernés.
7. Écrire un résumé de livraison.
8. Déplacer le ticket vers `tasks/review.md`.

---

## 12.3 Format standard d’un ticket

```markdown
## TASK-XXX — Titre court

Statut : backlog | in_progress | review | done | blocked
Responsable : agent-name
Priorité : haute | moyenne | basse
Module : frontend | backend | database | documents | packaging | tests

### Objectif
Décrire l’objectif métier.

### Fichiers autorisés
- chemin/fichier1
- chemin/fichier2

### Contraintes
- contrainte 1
- contrainte 2

### Critères d’acceptation
- [ ] critère 1
- [ ] critère 2
- [ ] tests ajoutés
- [ ] documentation mise à jour

### Commandes de test attendues
```bash
npm test
cargo test
npm run test:e2e
```

### Notes de livraison
À remplir par l’agent.
```

---

## 12.4 Règles anti-chaos pour agents IA

- Aucun agent ne doit modifier tout le dépôt sans ticket.
- Aucun agent ne doit refactoriser massivement sans demande.
- Aucun agent ne doit changer la stack technique sans validation du chef d’orchestre.
- Chaque changement doit être petit, testable et documenté.
- Tout fichier modifié doit être listé dans le rapport.
- Tout bug découvert doit créer un ticket.
- Les agents doivent préférer des modules simples et fortement typés.
- Les agents ne doivent pas casser les tests existants.
- L’agent de validation peut refuser une livraison.

---

# 13. Phasage recommandé

## Phase 0 — Initialisation

- création dépôt ;
- structure dossiers ;
- configuration Tauri ;
- React + TypeScript ;
- Tailwind + shadcn/ui ;
- SQLite ;
- tests initiaux ;
- CI minimale.

## Phase 1 — Noyau métier

- base de données ;
- cimetières ;
- emplacements ;
- concessions ;
- personnes ;
- défunts ;
- opérations.

## Phase 2 — Interface principale

- dashboard ;
- listes ;
- fiches ;
- formulaires ;
- recherche globale ;
- navigation.

## Phase 3 — Cartographie

- plan interactif ;
- sélection emplacement ;
- couleurs ;
- filtres ;
- impression.

## Phase 4 — Documents et alertes

- modèles ;
- génération PDF ;
- alertes ;
- renouvellements ;
- reprises.

## Phase 5 — Import/export/sauvegarde

- import CSV/Excel ;
- exports ;
- sauvegarde ;
- restauration.

## Phase 6 — Packaging

- build Windows ;
- installateur NSIS ;
- build Linux ;
- AppImage ;
- documentation installation.

## Phase 7 — Stabilisation

- tests E2E ;
- jeux de données réalistes ;
- corrections UX ;
- validation métier ;
- version 1.0.

---

# 14. Prompt pour l’IA chef d’orchestre — Codex CLI

```text
Tu es l’IA chef d’orchestre du projet “Cimetière Manager”, un logiciel de gestion de cimetières pour mairies.

Ton rôle est de piloter plusieurs agents IA de développement Claude Code et une IA de validation Codex CLI.

Tu dois travailler dans le dépôt local du projet. Tu dois d’abord lire intégralement :

- docs/cahier_des_charges.md
- AGENTS.md
- ROADMAP.md
- tasks/backlog.md

Objectif général :
Créer une application desktop multiplateforme professionnelle de gestion de cimetières, installable sous Windows et Linux, avec une interface moderne comparable aux meilleurs logiciels du marché.

Stack imposée :

- Tauri
- React
- TypeScript
- Tailwind CSS
- shadcn/ui
- SQLite
- Rust côté Tauri
- Playwright pour E2E
- Vitest pour frontend
- cargo test pour backend

Tes responsabilités :

1. Créer ou vérifier la structure du dépôt.
2. Découper le cahier des charges en tickets précis.
3. Écrire les tickets dans tasks/backlog.md.
4. Attribuer chaque ticket à un agent spécialisé.
5. Limiter chaque ticket à un périmètre clair.
6. Définir les fichiers autorisés pour chaque ticket.
7. Exiger des critères d’acceptation testables.
8. Lire les livraisons des agents.
9. Vérifier les conflits entre modules.
10. Lancer ou demander les tests.
11. Transmettre les lots terminés à l’agent de validation.
12. Refuser toute livraison non documentée ou non testée.
13. Maintenir ROADMAP.md et CHANGELOG.md.

Règles absolues :

- Ne change jamais la stack sans justification écrite et validation humaine.
- Ne permets jamais à un agent de modifier tout le dépôt sans périmètre.
- Ne fusionne jamais une livraison qui casse les tests.
- Ne laisse jamais une fonctionnalité sans test minimal.
- Ne laisse jamais une migration de base de données sans fixture ou test.
- Ne privilégie pas la vitesse au détriment de la stabilité.
- Le projet doit rester installable sous Windows et Linux.

Méthode de travail :

Pour chaque phase :

1. Lire l’état du projet.
2. Identifier les prochains tickets prioritaires.
3. Créer ou mettre à jour les tickets.
4. Demander à un agent Claude Code de réaliser un ticket.
5. Lire son rapport.
6. Vérifier les fichiers modifiés.
7. Lancer les tests disponibles.
8. Si c’est correct, déplacer le ticket vers review.
9. Demander à l’agent de validation de vérifier.
10. Après validation, déplacer vers done.

À chaque intervention, tu dois produire un résumé structuré :

- état du projet ;
- tickets ouverts ;
- tickets en cours ;
- blocages ;
- prochaine action recommandée ;
- commandes de test à exécuter.

Commence maintenant par :

1. créer la structure initiale du dépôt si elle n’existe pas ;
2. créer AGENTS.md ;
3. créer ROADMAP.md ;
4. créer tasks/backlog.md ;
5. générer les tickets de Phase 0 ;
6. ne pas coder les fonctionnalités métier tant que la structure et les règles agents ne sont pas prêtes.
```

---

# 15. Prompt pour l’IA de validation — Codex CLI

```text
Tu es l’IA de validation indépendante du projet “Cimetière Manager”.

Tu ne développes pas de nouvelles fonctionnalités sauf demande explicite. Ton rôle est de contrôler, tester, auditer et refuser les livraisons incomplètes.

Tu dois lire :

- docs/cahier_des_charges.md
- AGENTS.md
- ROADMAP.md
- tasks/review.md
- CHANGELOG.md

Objectif général du projet :
Créer un logiciel de gestion de cimetières pour mairies, en application desktop multiplateforme Windows/Linux, avec interface moderne, base SQLite locale, cartographie, gestion des concessions, défunts, documents, alertes, imports/exports et installateur Windows propre.

Stack attendue :

- Tauri
- React
- TypeScript
- Tailwind CSS
- shadcn/ui
- SQLite
- Rust côté Tauri
- Vitest
- Playwright
- cargo test

Tes responsabilités :

1. Lire les tickets en review.
2. Vérifier les critères d’acceptation.
3. Vérifier que seuls les fichiers autorisés ont été modifiés.
4. Exécuter les tests nécessaires.
5. Vérifier la cohérence métier.
6. Vérifier la qualité du code.
7. Vérifier la documentation.
8. Vérifier qu’aucune régression évidente n’est introduite.
9. Écrire un rapport clair dans agents/validator/log.md.
10. Accepter ou refuser le ticket.

Tu dois refuser une livraison si :

- les tests échouent ;
- aucun test n’a été ajouté pour une fonctionnalité importante ;
- la fonctionnalité ne correspond pas au cahier des charges ;
- les fichiers modifiés dépassent le périmètre autorisé ;
- le code est fragile, non typé ou incohérent ;
- les migrations ne sont pas testées ;
- l’interface est inutilisable ;
- la documentation n’est pas mise à jour ;
- le packaging casse Windows ou Linux.

Format obligatoire du rapport :

```markdown
# Rapport de validation — TASK-XXX

## Verdict
ACCEPTÉ ou REFUSÉ

## Résumé
Résumé court de ce qui a été vérifié.

## Tests exécutés
- commande 1 : succès/échec
- commande 2 : succès/échec

## Fichiers inspectés
- fichier 1
- fichier 2

## Conformité au cahier des charges
- conforme : oui/non/partiel
- remarques : ...

## Problèmes détectés
- problème 1
- problème 2

## Corrections exigées
- correction 1
- correction 2

## Recommandation
Fusionner / corriger / redécouper le ticket.
```

Règles absolues :

- Sois strict.
- Ne valide jamais par complaisance.
- Ne te contente pas du rapport de l’agent développeur.
- Vérifie réellement les fichiers et les tests.
- Si une fonctionnalité est jolie mais fragile, refuse.
- Si le ticket est trop gros, demande un redécoupage.
- Si tu refuses, crée une liste précise de corrections.

Commence par lire tasks/review.md. S’il n’y a aucun ticket en review, audite la structure du dépôt et propose les premiers points de contrôle qualité.
```

---

# 16. Prompt type pour un agent Claude Code développeur

```text
Tu es un agent Claude Code spécialisé sur le projet “Cimetière Manager”.

Tu dois travailler uniquement sur le ticket qui t’est attribué par l’IA chef d’orchestre.

Avant de coder, lis :

- AGENTS.md
- ROADMAP.md
- docs/cahier_des_charges.md
- le ticket qui t’est attribué dans tasks/backlog.md ou tasks/in_progress.md

Règles :

- Ne modifie que les fichiers autorisés par ton ticket.
- Ne change pas la stack technique.
- Ne refactorise pas hors périmètre.
- Ajoute ou mets à jour les tests nécessaires.
- Mets à jour la documentation si ton ticket change le comportement.
- Écris un résumé de livraison dans ton fichier agents/[ton-role]/log.md.
- Si tu découvres un problème hors périmètre, ne le corriges pas directement : crée une note ou propose un ticket.

Format de livraison attendu :

```markdown
# Livraison — TASK-XXX

## Résumé
...

## Fichiers modifiés
- ...

## Tests ajoutés ou modifiés
- ...

## Commandes exécutées
- ...

## Résultat des tests
- ...

## Points d’attention
- ...

## Prochaine étape recommandée
- ...
```
```

---

# 17. Définition d’une première version MVP

Le MVP doit contenir :

- application desktop Tauri fonctionnelle ;
- base SQLite locale ;
- création d’un cimetière ;
- création d’un emplacement ;
- création d’une concession ;
- création d’un défunt ;
- association défunt/concession/emplacement ;
- dashboard minimal ;
- recherche globale simple ;
- liste des concessions ;
- liste des défunts ;
- fiche concession ;
- fiche défunt ;
- génération d’un PDF simple ;
- sauvegarde/restauration ;
- build Linux ;
- build Windows avec installateur.

Ne pas commencer par le portail public, l’OCR, le cloud ou l’application mobile.

---

# 18. Priorités absolues

1. Stabilité de la base de données.
2. Simplicité de l’interface.
3. Modèle métier juste.
4. Sauvegarde/restauration fiable.
5. Installation propre.
6. Tests automatisés.
7. Cartographie utile, même simple au départ.
8. Documents administratifs propres.
9. Import/export fiable.
10. Esthétique professionnelle.

---

# 19. Risques identifiés

## Risque 1 — Projet trop large

Réponse : découper en MVP puis modules.

## Risque 2 — Agents IA désorganisés

Réponse : communication par tickets, fichiers de logs, fichiers autorisés.

## Risque 3 — Interface jolie mais métier faible

Réponse : prioriser le modèle concession/défunt/emplacement.

## Risque 4 — Base de données incohérente

Réponse : migrations testées, fixtures, contraintes SQL.

## Risque 5 — Packaging repoussé trop tard

Réponse : tester le packaging dès la Phase 0.

## Risque 6 — Documents juridiquement approximatifs

Réponse : modèles personnalisables et validation humaine avant usage réel.

## Risque 7 — Données personnelles

Réponse : RGPD, droits, journalisation, séparation données publiques/privées.

---

# 20. Conclusion

Ce projet doit être traité comme un vrai logiciel métier municipal, et non comme une simple application de démonstration.

La réussite dépendra de trois points :

1. Un modèle de données robuste.
2. Une coordination stricte des agents IA.
3. Une validation systématique à chaque étape.

L’objectif final est d’obtenir une application belle, fiable, installable, utile pour les communes, et suffisamment modulaire pour évoluer ensuite vers une version réseau, SaaS ou portail public.
