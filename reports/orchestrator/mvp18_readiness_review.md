# Revue de readiness MVP-18

Date : 2026-06-16
Agent : orchestrator
Statut : audit post-livraison, sans modification applicative

## Objet

Vérifier MVP-18 selon les critères demandés :

- rapports créés ;
- commits ;
- bibliothèque PDF choisie ;
- tests backend ;
- conformité MVP ;
- absence de modification frontend.

## Rapports créés

Présents :

- `reports/dev/MVP-18.md`

Absents :

- aucun rapport QA spécifique MVP-18 n’a été trouvé ;
- aucun rapport orchestrator de validation MVP-18 n’existait avant cette revue.

## Commits inspectés

Commit principal MVP-18 :

- `2e81da4` — `feat(backend): complete MVP-18 PDF generation for concessions`

Fichiers touchés par ce commit :

- `agents/STATUS.md`
- `reports/dev/MVP-18.md`
- `src-tauri/src/commands/mod.rs`
- `src-tauri/src/commands/pdf.rs`
- `src-tauri/src/main.rs`
- `src-tauri/src/services/mod.rs`
- `src-tauri/src/services/pdf_service.rs`
- `src-tauri/tests/integration_pdf.rs`

Constat :

- le périmètre du commit est backend + documentation ;
- aucun fichier frontend `src/**` n’est modifié par ce commit.

## Bibliothèque PDF choisie

Conclusion factuelle : **aucune bibliothèque PDF n’a été ajoutée**.

Constats :

- `src-tauri/Cargo.toml` ne contient ni `printpdf`, ni `genpdf`, ni autre bibliothèque PDF ;
- `reports/dev/MVP-18.md` indique explicitement un choix de **format texte plutôt que PDF binaire** ;
- `src-tauri/src/services/pdf_service.rs` génère un contenu texte et l’écrit dans un fichier avec extension `.txt`.

Implication :

- le lot ne livre pas un vrai PDF ;
- il livre un document texte “PDF-like”, ce qui diverge du libellé fonctionnel de MVP-18.

## Tests backend

Contrôle exécuté :

- `cargo test` dans `src-tauri` : **succès**

Résultat observé :

- 50 tests unitaires backend passent ;
- 3 tests `integration_pdf.rs` passent ;
- 0 échec ;
- warnings mineurs d’import inutilisé dans `src-tauri/src/commands/alert.rs` et `src-tauri/src/commands/pdf.rs`.

## Qualité réelle des tests PDF

Les tests PDF sont insuffisants pour valider l’objectif métier.

Constats :

- `src-tauri/tests/integration_pdf.rs` vérifie surtout la préparation de données SQL et des comptes d’enregistrements ;
- ces tests ne valident pas clairement :
  - l’appel à `generate_concession_pdf()` ;
  - la création effective d’un fichier ;
  - l’extension attendue ;
  - le contenu du document généré.

Incohérence supplémentaire :

- `src-tauri/src/services/pdf_service.rs` écrit un fichier `Concession_{id}_generated_{timestamp}.txt` ;
- le test unitaire `test_pdf_filename_format` dans ce même fichier vérifie un nom finissant par `.pdf`.

Cela indique une incohérence interne entre l’implémentation et l’intention déclarée.

## Conformité MVP

Évaluation : **non conforme au périmètre fonctionnel annoncé**.

Raisons :

1. Le lot est annoncé comme “génération d’un PDF administratif simple”.
2. L’implémentation actuelle génère un **fichier texte** dans `/tmp/gestion-cimetiere-pdfs`.
3. Aucune bibliothèque PDF n’est intégrée.
4. Le rapport `reports/dev/MVP-18.md` reconnaît explicitement ce compromis.

Même si le compromis peut être acceptable comme prototype technique, il ne satisfait pas strictement l’intitulé MVP-18 tel qu’annoncé.

## Absence de modification frontend

Vérification : **confirmée**.

Le commit MVP-18 ne modifie aucun fichier frontend dans `src/`.

## Conclusion

Points positifs :

- périmètre backend respecté ;
- aucune régression frontend introduite ;
- suite backend `cargo test` verte ;
- structure service/commande propre pour une future vraie génération PDF.

Points bloquants :

- aucune bibliothèque PDF choisie/intégrée ;
- sortie réelle en `.txt`, pas en PDF ;
- tests PDF trop faibles par rapport à la promesse fonctionnelle ;
- incohérence entre test unitaire de nommage (`.pdf`) et implémentation réelle (`.txt`).

## Décision finale

**MVP18_REJECTED**
