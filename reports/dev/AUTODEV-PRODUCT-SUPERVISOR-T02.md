objectif
- Corriger l'ensemble du contrat T02 pour que `load_product_plan()` et `enforce_specifications_for_plan()` traitent correctement les spécifications absentes et existantes sur `approved-only`, `draft` et `autonomous`, avec persistance systématique des métadonnées de traçabilité exigées.

fichiers modifiés
- `autodev/src/autodev/product_plan.py`
- `autodev/tests/test_specification_policy.py`
- `reports/dev/AUTODEV-PRODUCT-SUPERVISOR-T02.md`

décisions prises
- La persistance des métadonnées de validation a été factorisée dans `product_plan.py` pour s'appliquer aux spécifications générées et réutilisées.
- `enforce_specifications_for_plan()` recharge désormais les métadonnées existantes en mode tolérant pour `draft` et `autonomous`: si elles sont absentes, invalides ou périmées, la validation de la spécification est rejouée puis la trace est régénérée avant la barrière.
- `approved-only` conserve son comportement strict: aucune génération implicite, aucune réécriture de validation déjà acquise, et rejet immédiat si les métadonnées approuvées sont absentes ou invalides.
- `draft` persiste maintenant aussi ses métadonnées pour une spécification déjà existante avant de lever le blocage `REQUEST_HUMAN`, avec commit courant, origine documentaire dans le prompt et statut `pending-human`.
- `autonomous` persiste maintenant aussi ses métadonnées pour une spécification déjà existante et régénère les validations invalides ou périmées avec le commit courant, le prompt de validation contractuelle et le statut `approved` ou `draft` selon le résultat.
- Les tests d'intégration couvrent explicitement les chemins réels demandés pour les spécifications existantes avec métadonnées absentes, invalides et périmées, ainsi que la préservation d'une validation humaine existante en `approved-only`.

problèmes connus
- Trois tests liés à la validation JSON Schema restent sautés quand `jsonschema` n'est pas installé dans l'environnement.

résultats des tests
- `env PYTHONPATH=autodev/src python -m pytest autodev/tests/test_product_plan.py autodev/tests/test_specification_policy.py -q` : `130 passed, 3 skipped`
- `env PYTHONPATH=autodev/src python -m pytest autodev/tests -q` : `290 passed, 3 skipped`
- `git diff --check` : OK

prochaine étape
- Étendre au besoin les revues contractuelles futures avec la même matrice de traçabilité pour toute nouvelle politique ou tout enrichissement du schéma de validation.
