# T1 — Extension du schéma SQLite des concessions

## Objectif

Ajouter une migration SQLite incrémentale, non destructive et rejouable pour stocker les données minimales nécessaires au cycle de vie des concessions.

## Fichiers modifiés

- `src-tauri/migrations/0007_extend_concessions_for_lifecycle.sql`
- `src-tauri/src/db/migrations.rs`
- `reports/dev/MVP-CL-01.md`

## Migration et colonnes ajoutées

La migration `0007_extend_concessions_for_lifecycle.sql` ajoute uniquement les champs requis pour cette feature :

- `concession_number`
- `concession_type`
- `duration_years`
- `start_date`
- `holder_first_name`
- `holder_last_name`
- `holder_address`
- `holder_postal_code`
- `holder_commune`
- `observations`

Aucune table, colonne ou donnée existante n’est supprimée.

## Mécanisme de migrations

Le suivi des migrations est implémenté dans `src-tauri/src/db/migrations.rs`.

`run_migrations()` :

- crée la table interne `schema_migrations` avant de la consulter ;
- vérifie si la migration `0007_extend_concessions_for_lifecycle` est déjà appliquée ;
- exécute la migration dans une transaction lorsqu’elle est absente ;
- enregistre la migration uniquement après son exécution réussie ;
- ne rejoue pas la migration lors d’un second appel.

Le fichier `src-tauri/migrations/001_initial_schema.sql` n’est pas modifié par T1.

## Compatibilité avec une base existante

Les tests construisent une base représentant le schéma antérieur à la migration 0007, insèrent des données existantes, puis appliquent `run_migrations()`.

Ils vérifient :

- la conservation des concessions historiques ;
- la présence des nouvelles colonnes ;
- la conservation des anciennes valeurs ;
- la valeur `NULL` des nouveaux champs pour les anciennes lignes ;
- l’idempotence d’un second appel ;
- l’enregistrement unique de la migration 0007.

## Numéro de concession

Pour préserver les données historiques, `concession_number` reste nullable dans cette migration.

Lorsqu’un numéro non vide est renseigné :

- l’unicité est évaluée sur `lower(trim(concession_number))` ;
- les différences de casse ou les espaces périphériques ne permettent pas de créer un doublon.

La migration SQLite autorise encore les valeurs `NULL`, vides ou composées uniquement d’espaces afin de préserver la compatibilité avec les données historiques. Le backend imposera un numéro non vide et normalisé lors des nouvelles créations et modifications.

## Résultats des validations

Commandes réellement exécutées :

- `cargo test -p gestion-cimetiere db::migrations`
- `cargo fmt --check --manifest-path src-tauri/Cargo.toml`

Résultats :

- tests des migrations : succès ;
- formatage Rust : succès.

## Problèmes connus

Le contrôle métier d’occupation incompatible d’un emplacement ne relève pas de cette tâche de migration. Il sera implémenté dans les tâches backend chargées de la création et de la modification des concessions.

## Prochaine étape

T2 adaptera le modèle métier Rust, les DTO et le repository au schéma intégré par T1.
