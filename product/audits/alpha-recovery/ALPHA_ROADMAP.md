# Alpha Roadmap

Date d'audit : 2026-07-11

## Positionnement proposé

Le bon objectif n'est plus "confirmer un MVP déjà prêt". Le bon objectif est "atteindre une alpha réellement exploitable par une mairie pilote sur un poste local".

## Alpha 1

Nom : saisir les données cœur

But :
- permettre à une mairie vide de démarrer sans terminal.

Livrables attendus :
- écran réel de liste et création des cimetières ;
- écran réel de liste et création des emplacements ;
- création et édition de concessions ;
- création et édition de personnes et défunts ;
- navigation fiable liste -> fiche -> retour.

Critère de sortie :
- un agent peut créer un cimetière, un emplacement, une concession et un défunt depuis l'UI.

## Alpha 2

Nom : relier les entités métier

But :
- transformer les objets isolés en dossier cimetière exploitable.

Livrables attendus :
- association concession <-> emplacement ;
- association concession <-> concessionnaire / ayant droit ;
- association concession <-> défunt via inhumation ;
- ouverture des fiches depuis recherche et listes ;
- carte branchée aux vraies données.

Critère de sortie :
- un agent peut retrouver un défunt, ouvrir sa fiche et le localiser sur le plan réel.

## Alpha 3

Nom : fiabiliser exploitation et sécurité locale

But :
- rendre le poste de travail administrativement sûr.

Livrables attendus :
- sauvegarde et restauration réellement fonctionnelles ;
- recalcul et traitement des alertes depuis l'UI ;
- confirmations de suppression et messages de succès/erreur cohérents ;
- stockage base/sauvegardes dans des emplacements applicatifs OS.

Critère de sortie :
- un agent peut créer une sauvegarde, la voir, restaurer, puis vérifier la récupération des données sans terminal.

## Alpha 4

Nom : documents et parcours administratifs

But :
- couvrir les actions visibles et utiles du quotidien mairie.

Livrables attendus :
- PDF concession lisible avec titulaire et défunts ;
- fiche défunt exportable ;
- statuts concession réellement modifiables ;
- alertes d'échéance exploitables ;
- premières preuves UI des parcours de renouvellement.

Critère de sortie :
- un agent peut traiter une concession arrivant à échéance et produire un document simple.

## Alpha 5

Nom : preuve packagée

But :
- cesser de raisonner sur la théorie du dépôt et prouver l'usage packagé.

Livrables attendus :
- installateur Windows testé ;
- AppImage ou `.deb` testé ;
- jeu de données de démonstration packagé ou procédure simple d'initialisation ;
- campagne E2E réellement exécutable contre la build ;
- compte rendu de validation utilisateur "sans terminal".

Critère de sortie :
- une personne non technique peut installer, lancer, saisir, rechercher, sauvegarder et générer un PDF.

## Hors alpha immédiate

À repousser après alpha exploitable :
- portail public ;
- QR codes ;
- import CSV avancé ;
- droits utilisateurs complets ;
- journal d'audit complet ;
- documents associés ;
- procédures de reprise complètes ;
- statistiques avancées.

## Risque principal à piloter

Le projet échoue si l'équipe continue à confondre :
- présence de code backend ;
- présence d'un écran ;
- validation réelle d'une opération packagée.

Le prochain pilotage doit imposer une règle simple :
- une fonctionnalité n'existe que lorsqu'un agent municipal peut la terminer à l'écran, sur la build, avec une preuve UI et un test E2E utile.
