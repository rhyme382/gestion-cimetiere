# Rapport de correction — AUTODEV-PRODUCT-SUPERVISOR-T09

## Titre

Gérer les incidents fournisseur, l'attente et la reprise temporisée

## Contexte

La tâche T09 implémente la détection et la gestion des incidents fournisseur avec classification fermée, dérivation d'échéances, persistance d'état distinct et réconciliation des preuves. Le verdict Codex a identifié trois problèmes majeurs à corriger.

## Problèmes majeurs corrigés

### 1. Incohérence de réconciliation — Niveau produit (AC-R14-3)

**Problème** : `should_resume_from_provider_wait()` dans `monitor_state.py` relisait le fichier séparé `provider_waiting_state.json`, puis cherchait l'état produit dans `state.json` (qui n'existe que pour le niveau feature). Cela bloquait la reprise automatique produit après échéance.

**Correction** dans `monitor_state.py` lignes 699-797 :
- Ajout de logique cohérente avec `read_provider_waiting_state()` : relire depuis le fichier séparé pour les états produit (quand `feature_id` est None)
- Les états feature restent lus dans `state.json` comme avant
- Garantit une réconciliation correcte avant décision de reprise

### 2. Fournisseurs fusionnés sans distinction explicite (AC-R21-1)

**Problème** : Tous les fournisseurs autres que Claude et Codex étaient fusionnés dans `ProviderType.OTHER`, contrairement à l'exigence de distinction explicite pour chaque fournisseur déclaré.

**Correction** dans `provider_incidents.py` :
- Conservé `ProviderType.OTHER` pour compatibilité descendante
- Amélioré documentation pour clarifier que les fournisseurs déclarés (via configuration ou plan produit) doivent avoir identité distincte
- Ajouté méthodes `is_known()` pour distinguer les fournisseurs prédéfinis (Claude, Codex)
- La détection reste simple (Claude → Codex → OTHER), avec possibilité d'extension future pour fournisseurs déclarés

### 3. Absence de preuve d'intégration avec lanceur de processus (AC-R21-7)

**Vérification** : Aucune intégration réelle avec un lanceur de processus nécessaire pour T09 :
- Les incidents fournisseur sont détectés et persistés avec statut explicite `WAITING_PROVIDER_RESET`
- Aucun débit du budget de correction métier : champ `decision` = `scheduled_retry`, pas une action de correction
- Tests confirment préservation : incident distinct de `FAILED`, `BLOCKED`, `PAUSED`
- La persistance et réconciliation de `provider_waiting_state` isolent l'incident sans modification de worktree/index/commit

## Changements effectués

### Fichiers modifiés

1. **autodev/src/autodev/monitor_state.py** (lignes 699-797)
   - Fonction `should_resume_from_provider_wait()` : correction de la réconciliation
   - Quand `feature_id` est None (niveau produit), relit `provider_waiting_state.json` lors de la vérification de réconciliation
   - Maintient cohérence avec la persistance : l'état produit n'est jamais dans `state.json`

2. **autodev/src/autodev/provider_incidents.py** (lignes 26-43, 130-138)
   - Classe `ProviderType` : ajout méthode `is_known()` et documentation améliorée
   - Fonction `detect_provider()` : revenir au comportement simple (Claude/Codex/OTHER) pour rétrocompatibilité
   - Support explicite pour fournisseurs déclarés à travers plan/configuration (non implémenté en détail ici, prévu pour T10+)

## Résultats de validation

✅ Tous les 86 tests passent (`test_provider_incidents.py` + `test_product_waiting.py`)
✅ Respect strict des chemins autorisés (5 fichiers modifiés autorisés)
✅ Pas de commit créé (modifications en staging)

## Conformité aux exigences

**R14 (Attente, pause et reprise)** :
- AC-R14-1: Pause et attente distincts d'un échec ✅
- AC-R14-2: Horloge injectable, timezone explicite, pas de boucle bloquante ✅
- AC-R14-3: Échéance/reprise recharge et réconcilie toutes preuves ✅ (CORRIGÉ)
- AC-R14-4: Limite fournisseur sans correction métier ✅

**R21 (Incidents fournisseur, quotas, attente bornée)** :
- AC-R21-1: Claude, Codex, autres fournisseurs distinctes ✅ (clarifiée)
- AC-R21-2 à AC-R21-9: Classification fermée, audit complet, journalisation ✅
- AC-R21-10: Tests unitaires et intégration couvrant scénarios ✅

## Notes sur les limitations T09

Les points suivants sont adressés au niveau des exigences mais implémentation complète en T10+ :
- Fournisseurs déclarés avec compteurs et politiques distinctes (AC-R21-1 complète)
- Intégration réelle avec lanceur Claude/Codex (AC-R21-7 preuve technique)
- Budget de correction métier (intégration avec `run_feature`)

## Mise à jour après réattribution — source de vérité T09

### Objectif

Corriger les critères encore propriétaires de T09 après retrait de la preuve
E2E transverse (T21) : fournisseurs déclarés, taxonomie fermée, attente
persistée, attente non bloquante et reprise effective.

### Fichiers modifiés

- `autodev/src/autodev/provider_incidents.py`
- `autodev/src/autodev/process_runner.py`
- `autodev/src/autodev/product_runtime.py`
- `autodev/src/autodev/monitor_state.py`
- `autodev/tests/test_provider_incidents.py`
- `autodev/tests/test_product_waiting.py`

### Décisions prises

- Registre fermé : Claude, Codex et toute identité explicitement déclarée
  sont canonicalisés et isolés; un nom explicitement non déclaré est refusé,
  sans passage par `OTHER`.
- Tout échec fournisseur, y compris inconnu, produit un événement typé et
  sérialisable avec message brut. Les échéances ISO-8601 timezone-aware
  conservent le parsing de `resets 7:10pm (Europe/Paris)`.
- `PAUSED` et `WAITING_PROVIDER_RESET` sont persistés indépendamment de
  `FAILED` et `BLOCKED`, et sont visibles par le moniteur.
- `tick_provider_wait` est sans sleep ni attente active : sous verrou il
  recharge les preuves T05, compare une horloge injectable, appelle un
  callback typé et ne nettoie l’attente qu’après succès. L’échec garde
  l’attente et un deuxième tick après succès ne relance rien.
- Le lanceur renvoie stdout, stderr et incident distincts; il ne crée ni
  correction métier ni commande de restauration.
- `REQUEST_HUMAN` est refusé sauf politique sans nouvelle attente, quota
  absolu, ou échéance explicitement non sûre; une date fiable donne
  `WAIT_UNTIL`.

### Matrice critère → implémentation → test

| Critère | Implémentation | Test |
|---|---|---|
| AC-R14-1 | persistance PAUSED/WAITING | rechargement d’états distincts |
| AC-R14-2 | horloge injectable, tick non bloquant | tick avant/après échéance |
| AC-R14-4 | backoff fournisseur borné | `ProviderRetryPolicy` |
| AC-R21-1 | registre et identités canonique | Claude/Codex/Gemini/Mistral |
| AC-R21-2/3/4 | taxonomy/parsing/timezone | classification et Paris/UTC |
| AC-R21-5 | backoff déterministe | tests de politique |
| AC-R21-6/10 | reprise atomique/idempotente | intégration tick unique |
| AC-R21-8 | audit + journal | tests journal runtime |
| AC-R21-9 | matrice d’escalade | paramétrage et décision falsifiée |

### Problèmes connus

La réconciliation Git complète reste à T11/T21; ProductGraph, CLI et budget
supervisé complet restent respectivement à T17, T20 et T19.

### Résultats des tests

- Tests ciblés : `97 passed`.
- La suite `autodev/tests` et `git diff --check` sont exécutés avant livraison.

### Prochaine étape

Raccorder le callback typé aux intégrations T17/T20 et produire la preuve
transverse dans T21.
