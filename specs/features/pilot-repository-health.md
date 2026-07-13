# FEATURE-PILOT-001 — Diagnostic technique du dépôt

## Objectif

Ajouter au logiciel un mécanisme interne permettant de vérifier que les composants essentiels de l'application peuvent être initialisés correctement.

Cette fonctionnalité sert de pilote pour valider la chaîne de développement automatisée.

## Comportement attendu

Le backend Rust doit exposer une commande Tauri de diagnostic.

Cette commande doit retourner un résultat structuré comprenant :

- l'état général ;
- la disponibilité de la base SQLite ;
- la version de l'application ;
- un message lisible en cas d'échec.

Le frontend doit pouvoir appeler cette commande et afficher le résultat dans une zone de diagnostic technique.

## Règles

- Le diagnostic ne doit modifier aucune donnée métier.
- Aucun accès réseau ne doit être nécessaire.
- Une erreur SQLite doit être retournée proprement, sans panic.
- Le résultat doit être typé côté Rust et côté TypeScript.
- Les conventions existantes du dépôt doivent être respectées.
- Aucun nouveau framework ne doit être ajouté.

## Critères d'acceptation

1. Une commande Tauri de diagnostic existe.
2. La commande retourne un objet structuré.
3. L'état SQLite est vérifié sans modifier la base.
4. Les erreurs sont converties en résultat exploitable par le frontend.
5. Le frontend peut appeler la commande.
6. Le résultat peut être affiché dans l'interface.
7. Des tests couvrent le comportement nominal.
8. Des tests couvrent au moins un cas d'échec.
9. Les commandes de compilation et de tests existantes réussissent.

## Hors périmètre

- télémétrie ;
- envoi de données ;
- surveillance continue ;
- interface d'administration complète ;
- système générique de monitoring.
