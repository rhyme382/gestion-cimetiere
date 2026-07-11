# ORCHESTRATOR-PRODUCT-AUDIT

## objectif

Connecter la fondation LangGraph a un vrai workflow `audit` capable de lancer `codex exec`, produire les livrables d'audit produit, valider le backlog JSON et bloquer toute modification non autorisee hors perimetre.

## architecture

- `orchestrator/cli.py` orchestre la commande `audit`, ses options et les verdicts JSON.
- `orchestrator/audit.py` contient la detection de racine Git, l'inventaire des sources, la construction du prompt, l'archivage des livrables, les controles Git et la validation du backlog.
- `orchestrator/models/product_audit.py` definit le contrat Pydantic du backlog produit et ses validations structurelles et semantiques de base.
- `orchestrator/runners/codex_runner.py` encapsule `codex exec --sandbox workspace-write --cd <repo>` avec logs de session.

## commande

- Dry-run :
  `python -m orchestrator.cli audit --dry-run --verbose`
- Audit reel :
  `python -m orchestrator.cli audit --timeout 1800`
- Regeneration avec archivage :
  `python -m orchestrator.cli audit --force`

Options supportees :
- `--dry-run`
- `--force`
- `--timeout SECONDS`
- `--verbose`
- `--prompt PATH`
- `--output-root PATH`

## securite

- Le runner Codex utilise `--sandbox workspace-write` et n'active aucun mode dangereux.
- Le prompt interdit explicitement toute modification hors `product/**`, `tasks/backlog.json` et `reports/product/**`.
- Un snapshot Git avant/apres execution detecte les changements introduits hors perimetre et retourne `AUDIT_FAILED_UNAUTHORIZED_CHANGES`.
- Le workflow refuse d'ecraser des livrables existants sans `--force`.
- Avec `--force`, les anciens livrables sont copies sous `reports/product/archive/<timestamp>/`.

## validation

- Controle de presence des livrables obligatoires.
- Validation Pydantic du backlog `tasks/backlog.json`.
- Verification des IDs uniques, dependances connues et absence de cycle evident.
- Heuristiques minimales pour rejeter des criteres purement techniques non observables par un utilisateur.
- Verdicts explicites :
  `AUDIT_COMPLETED`, `AUDIT_FAILED_CODEX`, `AUDIT_FAILED_TIMEOUT`, `AUDIT_FAILED_MISSING_OUTPUT`, `AUDIT_FAILED_INVALID_BACKLOG`, `AUDIT_FAILED_EMPTY_BACKLOG`, `AUDIT_FAILED_UNAUTHORIZED_CHANGES`, `AUDIT_ALREADY_EXISTS`, `AUDIT_DRY_RUN`.

## tests

Tests unitaires mockes couverts :
- dry-run ;
- audit reussi ;
- retour Codex non nul ;
- timeout ;
- livrable absent ;
- backlog JSON invalide ;
- backlog vide ;
- IDs en doublon ;
- dependance inconnue ;
- modification interdite dans `src/` ;
- refus d'ecrasement ;
- archivage avec `--force`.

## limites connues

- La validation semantique du backlog reste heuristique ; elle ne remplace pas une revue produit humaine.
- Le runner parse le `session_id` seulement si Codex l'expose en stdout/stderr.
- Le controle Git compare l'etat avant/apres et ne reverte rien automatiquement, par choix de securite.
- Le dry-run verbose peut etre volumineux sur un depot large, meme si l'inventaire AppImage est maintenant borne aux sources utiles.

## procedure de lancement reel

1. Verifier que les livrables d'audit precedents sont absents ou utiliser `--force`.
2. Lancer :
   `python -m orchestrator.cli audit --timeout 1800 --verbose`
3. Consulter les logs sous :
   `orchestrator/logs/audit/<run_id>/`
4. Verifier le verdict JSON final et, en cas d'echec, inspecter `result.json`, `stdout.log` et `stderr.log`.
