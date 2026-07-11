# User Journeys

Date d'audit : 2026-07-11

## Principe

Chaque parcours répond à la question : un agent de mairie peut-il terminer ce travail dans l'application packagée, sans terminal ?

## Parcours 1

Nom : initialiser un nouveau cimetière

Objectif utilisateur :
- créer un cimetière ;
- créer ses emplacements ;
- commencer l'exploitation.

Étapes attendues :
1. Ouvrir la page `Cimetières`.
2. Créer un cimetière.
3. Enregistrer ses informations.
4. Ajouter des emplacements.
5. Vérifier le plan et les listes.

Constat :
- étape 1 possible ;
- étapes 2 à 5 impossibles.

Pourquoi :
- `src/pages/CemeteriesPage.tsx` est une page placeholder ;
- aucun formulaire ni action d'ajout ;
- l'écran Emplacements n'utilise pas les données du backend.

Verdict :
- échec complet.

## Parcours 2

Nom : enregistrer une concession complète

Objectif utilisateur :
- créer une concession ;
- la rattacher à un emplacement ;
- lui associer un concessionnaire.

Étapes attendues :
1. Aller sur `Concessions`.
2. Créer une concession.
3. Choisir le cimetière et l'emplacement.
4. Ajouter le concessionnaire.
5. Enregistrer.
6. Vérifier la fiche.

Constat :
- étape 1 possible ;
- étapes 2 à 5 impossibles ;
- étape 6 possible seulement pour des données déjà présentes.

Pourquoi :
- pas de bouton de création ni de formulaire ;
- pas d'écran personnes/concessionnaires ;
- les boutons d'action de la fiche ne sont pas branchés.

Verdict :
- échec complet sur l'usage métier principal.

## Parcours 3

Nom : ajouter un défunt puis le localiser

Objectif utilisateur :
- enregistrer un défunt ;
- l'associer à une concession ;
- le retrouver ensuite sur le plan.

Étapes attendues :
1. Aller sur `Défunts`.
2. Créer un défunt.
3. Associer la concession et l'inhumation.
4. Retrouver le défunt dans la recherche.
5. Ouvrir sa fiche.
6. Le localiser sur le plan réel.

Constat :
- consultation de liste possible si données existantes ;
- création impossible ;
- association impossible ;
- ouverture depuis la liste impossible ;
- localisation réelle impossible.

Pourquoi :
- aucune UI de création ;
- aucune UI pour `create_burial` ;
- bouton `Détails` non branché ;
- cartographie mockée.

Verdict :
- échec complet.

## Parcours 4

Nom : rechercher un défunt existant

Objectif utilisateur :
- saisir un nom ;
- retrouver une personne déjà enregistrée ;
- accéder à la fiche.

Étapes attendues :
1. Utiliser la barre de recherche ou la page `Recherche`.
2. Saisir le nom.
3. Voir les résultats.
4. Ouvrir la fiche.

Constat :
- étapes 1 à 3 possibles pour une première recherche simple ;
- étape 4 impossible depuis le bouton `Voir`.

Risques supplémentaires :
- une deuxième recherche dans la même session peut ne pas relancer la requête.

Verdict :
- partiellement réussi.

## Parcours 5

Nom : consulter une concession existante et éditer un PDF

Objectif utilisateur :
- ouvrir une concession déjà créée ;
- vérifier ses informations ;
- générer une fiche PDF.

Étapes attendues :
1. Ouvrir `Concessions`.
2. Filtrer si besoin.
3. Cliquer `Détails`.
4. Contrôler la fiche.
5. Cliquer `Générer PDF`.
6. Constater le succès.

Constat :
- parcours faisable si des concessions existent déjà.

Limites :
- le PDF reste très simple ;
- les actions `Éditer`, `Imprimer`, `Supprimer` sont inertes ;
- la fiche n'expose pas les champs administratifs attendus par le cahier des charges.

Verdict :
- réussi en lecture/export simple.

## Parcours 6

Nom : traiter les échéances

Objectif utilisateur :
- voir les concessions à surveiller ;
- ouvrir la fiche concernée ;
- acquitter l'alerte.

Étapes attendues :
1. Ouvrir le dashboard ou `Alertes`.
2. Voir les alertes à traiter.
3. Ouvrir la concession.
4. Acquitter l'alerte.

Constat :
- possible uniquement si des alertes existent déjà en base ;
- l'acquittement est branché ;
- aucun recalcul d'alertes n'est disponible en UI.

Verdict :
- partiellement réussi, non fiable pour le quotidien.

## Parcours 7

Nom : sauvegarder puis restaurer

Objectif utilisateur :
- créer une sauvegarde ;
- voir la liste des sauvegardes ;
- restaurer l'une d'elles en cas d'erreur.

Étapes attendues :
1. Aller sur `Sauvegardes`.
2. Créer une sauvegarde.
3. Voir la sauvegarde créée.
4. Demander une restauration.
5. Confirmer.
6. Reprendre le travail.

Constat :
- l'intention UI existe ;
- le contrat technique est cassé ;
- la restauration n'est pas exploitable.

Verdict :
- échec sur une fonction critique de production.

## Parcours 8

Nom : utiliser l'application packagée sur poste mairie

Objectif utilisateur :
- installer ;
- lancer ;
- travailler sans terminal.

Constat :
- les sources lues ne donnent pas de preuve finale d'installateurs Windows/AppImage/.deb testés jusqu'au bout ;
- plusieurs rapports release se contredisent ou restent en attente ;
- le stockage SQLite n'utilise pas encore un répertoire applicatif OS explicite.

Verdict :
- non prouvé.
