# User Journeys

Date d'audit : 2026-07-11

## Positionnement

Ces parcours décrivent la cible produit finale. Ils ne devalorisent pas le premier audit alpha ; ils l englobent et le dépassent.

## Parcours structurants

## Parcours 1

Nom : Initialiser la commune et ses cimetières

Etapes cibles :
1. Créer la fiche commune.
2. Créer un premier cimetière.
3. Définir ses sections, carrés, rangées et emplacements.
4. Renseigner horaires, règlement, plan et paramètres par défaut.

Constat actuel : Aujourd hui : impossible de terminer ce parcours sans terminal ni développement complémentaire.

## Parcours 2

Nom : Créer une concession complète

Etapes cibles :
1. Choisir le cimetière et l emplacement.
2. Créer la concession avec numéro, durée et dates.
3. Associer titulaire, cotitulaire et ayants droit.
4. Renseigner le tarif et l état de paiement.

Constat actuel : Aujourd hui : lecture partielle seulement, pas de chaîne de saisie complète.

## Parcours 3

Nom : Enregistrer un défunt puis une inhumation

Etapes cibles :
1. Créer la fiche défunt.
2. Sélectionner la concession.
3. Saisir l autorisation et la date d inhumation.
4. Vérifier la capacité restante et l historique.

Constat actuel : Aujourd hui : commande backend minimale mais pas de parcours utilisateur complet.

## Parcours 4

Nom : Traiter une échéance et renouveler

Etapes cibles :
1. Ouvrir le tableau de bord des échéances.
2. Ouvrir la concession concernée.
3. Calculer le renouvellement et la redevance.
4. Générer le document de renouvellement et enregistrer le paiement.

Constat actuel : Aujourd hui : alertes partielles, renouvellement non livré.

## Parcours 5

Nom : Piloter une procédure de reprise

Etapes cibles :
1. Identifier une concession potentiellement abandonnée.
2. Ouvrir un dossier de procédure.
3. Tracer constats, affichages, courriers et arrêtés.
4. Clôturer ou archiver le dossier.

Constat actuel : Aujourd hui : domaine absent du produit.

## Parcours 6

Nom : Gérer les urnes et espaces cinéraires

Etapes cibles :
1. Créer une niche ou cavurne.
2. Déposer une urne.
3. Tracer un retrait ou une dispersion.
4. Consulter l état du columbarium et du jardin du souvenir.

Constat actuel : Aujourd hui : domaine absent du produit.

## Parcours 7

Nom : Retrouver un dossier par recherche transversale

Etapes cibles :
1. Chercher par nom, famille, concession, emplacement ou contact.
2. Ouvrir le bon résultat.
3. Basculer vers la carte réelle.
4. Revenir au dossier sans perdre le contexte.

Constat actuel : Aujourd hui : recherche simple fragile et ouverture des résultats incomplète.

## Parcours 8

Nom : Consulter et éditer la cartographie

Etapes cibles :
1. Visualiser le plan réel du cimetière.
2. Localiser une concession ou un défunt.
3. Éditer une géométrie d emplacement.
4. Publier une nouvelle version du plan.

Constat actuel : Aujourd hui : consultation mockée, édition absente.

## Parcours 9

Nom : Joindre des pièces et générer des documents

Etapes cibles :
1. Ajouter un acte ou une photo.
2. Choisir un modèle administratif.
3. Générer un document sur le bon dossier.
4. Retrouver ce document dans l historique.

Constat actuel : Aujourd hui : un seul PDF simple, sans gestion de pièces ni historique documentaire.

## Parcours 10

Nom : Importer des données historiques

Etapes cibles :
1. Charger un CSV ou un Excel.
2. Mapper les colonnes.
3. Contrôler erreurs et doublons.
4. Valider ou annuler le lot.

Constat actuel : Aujourd hui : domaine absent du produit.

## Parcours 11

Nom : Administrer les utilisateurs et l audit

Etapes cibles :
1. Créer un compte local.
2. Assigner un rôle.
3. Contrôler les restrictions en UI et backend.
4. Relire le journal d audit.

Constat actuel : Aujourd hui : domaine absent du produit.

## Parcours 12

Nom : Sauvegarder, restaurer et mettre à jour

Etapes cibles :
1. Créer une sauvegarde.
2. Vérifier son intégrité.
3. Restaurer depuis l UI.
4. Installer une mise à jour sans perte de données.

Constat actuel : Aujourd hui : backend partiel, contrat UI cassé et preuve packagée incomplète.

## Lecture produit

La cible finale n'est pas un simple CRUD de concessions. C'est un poste municipal complet couvrant exploitation quotidienne, procédures réglementaires, documentaire, traçabilité, sécurité locale, restauration et accompagnement utilisateur.