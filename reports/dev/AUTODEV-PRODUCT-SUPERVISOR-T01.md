# Rapport de livraison — AUTODEV-PRODUCT-SUPERVISOR-T01

## Résumé exécutif

**CORRECTION CRITIQUE** : Le verdict Codex initial a identifié que l'identité de révision gelée n'était pas fiable car `ProductPlan.immutable_hash()` n'incluait pas tous les champs normatifs du plan (`generated_at` et `global_validations`).

La tâche **Ajouter le schéma et le chargeur du plan produit versionné** reste complète, avec une **correction décisive** appliquée au calcul du hash gelé pour assurer l'identification fiable de chaque révision du plan.

## Problème identifié par Codex

Le verdict Codex pointait que l'acceptation criterion **AC-R1-4** n'était pas satisfaite :
- La méthode `ProductPlan.immutable_hash()` ne hashait que `schema_version`, `plan_id`, `integration_branch`, `specification_policy` et les features.
- Elle ignorait les champs normatifs `generated_at` et `global_validations`.
- Deux plans différant uniquement sur ces champs produisaient le même hash, ce qui compromettait la traçabilité des révisions gelées.

## Corrections appliquées

### 1. `autodev/src/autodev/product_plan.py` — Méthode `immutable_hash()`

**Avant** (lignes 57-67) :
```python
def immutable_hash(self) -> str:
    feature_str = json.dumps(
        [f.to_dict() for f in self.features],
        sort_keys=True,
        separators=(",", ":"),
    )
    content = (
        f"{self.schema_version}|{self.plan_id}|{self.integration_branch}|"
        f"{self.specification_policy}|{feature_str}"
    )
    return hashlib.sha256(content.encode()).hexdigest()
```

**Après** (lignes 57-72) :
```python
def immutable_hash(self) -> str:
    feature_str = json.dumps(
        [f.to_dict() for f in self.features],
        sort_keys=True,
        separators=(",", ":"),
    )
    global_validations_str = json.dumps(
        self.global_validations,
        sort_keys=True,
        separators=(",", ":"),
    )
    content = (
        f"{self.schema_version}|{self.plan_id}|{self.generated_at}|"
        f"{self.integration_branch}|{self.specification_policy}|"
        f"{global_validations_str}|{feature_str}"
    )
    return hashlib.sha256(content.encode()).hexdigest()
```

**Impact** : Le hash inclut maintenant tous les champs normatifs du plan, garantissant que toute modification dans ces champs change le hash et facilite l'identification fiable de chaque révision gelée.

### 2. `autodev/tests/test_product_plan.py` — Tests de validation du hash

Ajout de deux tests supplémentaires dans la classe `TestProductPlanImmutability` :

**Test 1 — `test_plan_hash_changes_with_generated_at`** :
- Vérifie que deux plans différant par `generated_at` produisent des hashes différents.
- Critique pour garantir que chaque run avec un timestamp différent est identifié de manière unique.

**Test 2 — `test_plan_hash_changes_with_global_validations`** :
- Vérifie que deux plans différant par `global_validations` produisent des hashes différents.
- Critique pour distinguer les plans avec des stratégies de validation différentes.

## Résultats des tests

```bash
$ env PYTHONPATH=autodev/src python -m pytest autodev/tests/test_product_plan.py -q
.............................................                            [100%]
45 passed in 0.08s
```

**Verdict** : ✅ PASS
- Tous les 45 tests passent (43 tests existants + 2 nouveaux tests de validation du hash).
- Les deux nouveaux tests confirment que le hash change désormais correctement lors de modifications des champs normatifs.
- Aucune régression sur les tests existants.

## Conformité aux exigences

### R1 — Plan produit déclaratif et schéma versionné

| Critère | Statut | Preuve |
|---------|--------|--------|
| **AC-R1-1** : Schéma impose tous les champs | ✅ PASS | `product-plan.schema.json` impose `schema_version`, `plan_id`, `generated_at`, `integration_branch`, `specification_policy`, `features`, `global_validations` |
| **AC-R1-2** : Rejette doublons, cycles, dépendances inconnues | ✅ PASS | Validations dans `load_product_plan()` testées dans les suites existantes |
| **AC-R1-3** : Rejette statuts mutables | ✅ PASS | `validate_mutable_statuses()` appelle lors du chargement |
| **AC-R1-4** : Identité de révision gelée fiable | ✅ PASS (CORRIGÉ) | `immutable_hash()` inclut maintenant tous les champs normatifs ; confirmé par 2 nouveaux tests |

### Critères d'acceptation de la tâche

- ✅ Le chargeur refuse les versions inconnues, cycles, dépendances manquantes et doublons d'identifiants.
- ✅ **Le run fige une révision de plan et journalise l'identité de cette révision sans utiliser de statut mutable comme source de vérité.** — Maintenant garanti par le hash incluant tous les champs normatifs.
- ✅ Le schéma produit couvre les champs produit et feature exigés par la spécification.

## Contraintes respectées

- ✅ Aucune modification en dehors des chemins autorisés (`autodev/src/autodev/product_plan.py`, `autodev/tests/test_product_plan.py`).
- ✅ Aucun commit créé (modifications en attente pour révision).
- ✅ Les spécifications du projet restent inchangées.
- ✅ Tous les tests passent (45/45).

## Changements de comportement

La modification du calcul du hash est **intentionnelle et bénéfique** :
- Deux plans identiques à l'exception de `generated_at` ou `global_validations` produisent maintenant des hashes différents.
- Ceci améliore la traçabilité et élimine les collisions de hash qui compromettaient l'identification fiable des révisions.

Les révisions déjà gelées dans `frozen_revision.json` restent horodatées et immuables ; seules les futures révisions chargeront avec le nouveau hash.

## Conclusion

La tâche **AUTODEV-PRODUCT-SUPERVISOR-T01** satisfait maintenant tous les critères du verdict Codex initial. Le plan produit versionné est :

1. **Imposant** : Le schéma JSON et le chargeur exigent explicitement les champs critiques.
2. **Validant** : Les versions non supportées, cycles, dépendances, doublons et statuts mutables sont rejetés.
3. **Immuable** : La commande `run-product` fige une révision de plan identifiée de manière fiable et la journalise de manière append-only.
4. **Testée** : 45 tests, tous PASS, couvrant les cas nominaux, limites et la vérification du hash fiable.

Le système est prêt pour les tâches suivantes d'implémentation du superviseur produit.
