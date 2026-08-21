# AUTODEV-PRODUCT-SUPERVISOR-INVENTORY

## objectif

Établir un inventaire complet et exploitable de l'architecture Autodev actuelle afin de préparer l'implémentation d'un superviseur produit autonome capable d'orchestrer le cycle complet des features, de diagnostiquer les incidents réels et d'intégrer les features dans une base produit vérifiée. Cette mission reste documentaire ; l'implémentation appartient bien au périmètre de la feature spécifiée.

## fichiers modifiés

- `reports/dev/AUTODEV-PRODUCT-SUPERVISOR-INVENTORY.md`
- `.autodev/specifications/AUTODEV-product-orchestrator.md`

## inventaire de l'architecture actuelle

### 1. CLI et commandes existantes

La CLI principale est `autodev` via Typer (`autodev/src/autodev/cli.py`). Elle expose :

- `doctor`
- `plan`
- `run-task`
- `review-task`
- `correct-task`
- `integrate-task`
- `run-feature`
- `status`
- `monitor`
- `coverage`
- `migrate-backlog`

Constats :

- la couche CLI `autodev` est la plus riche, la plus testée et celle qui contient les invariants utiles pour un superviseur produit ;
- la couche `orchestrator/` expose une autre CLI Python basée sur `argparse` avec `init`, `audit`, `run`, `resume`, `status`, `approve`, `reject`, `cleanup`, mais elle reste plus générique et moins intégrée aux garde-fous d'`autodev`.
- l'orchestrateur Python doit rester le seul composant autorisé à appliquer la politique, muter Git, créer les commits d'intégration, gérer les checkpoints, les pauses et les reprises.

### 2. Couche `run-task`

`autodev/src/autodev/task_runner.py` prépare une branche `autodev/TASK-ID`, un worktree isolé `.autodev/worktrees/TASK-ID`, écrit les artefacts de run puis lance Claude en non interactif.

Comportements structurants déjà réutilisables :

- refus si le dépôt principal est sale ;
- refus si les dépendances de tâche ne sont pas intégrées ;
- prompt structuré avec backlog, critères propriétaires, `allowed_paths`, commandes de validation et contenu de `SPEC.md` ;
- exécution Claude via stdin ;
- détection explicite d'un faux succès lié à une demande de permissions ;
- filtrage des artefacts générés ;
- contrôle strict du scope Git ;
- validations de tâche rejouées après implémentation ;
- preuve obligatoire d'un commit produit au-dessus du commit de base.

### 3. Couche `review-task`

`autodev/src/autodev/review_task.py` relit une tâche en lecture seule avec Codex et un schéma JSON strict.

Comportements structurants déjà réutilisables :

- reconstruction du diff courant depuis `base_commit` vers le `HEAD` réel de la branche de tâche ;
- relance déterministe des validations avec contrôle qu'elles ne modifient pas le worktree ;
- vérification du `task-report.json` contre l'état Git et les validations courantes ;
- prompt de revue qui interdit d'utiliser des rapports narratifs historiques comme source de vérité ;
- prise en compte des dépendances déjà intégrées comme preuves héritées ;
- post-traitement Python du verdict pour imposer les règles de scope, de tests et de sévérité ;
- sortie normalisée par `autodev/schemas/review-result.schema.json`.

### 4. Couche `correct-task`

`autodev/src/autodev/correct_task.py` réutilise le worktree existant, rejoue Claude sur un prompt de correction et restaure automatiquement les chemins hors périmètre.

Comportements structurants déjà réutilisables :

- conservation de l'historique Git sans commit agent direct ;
- restauration sélective des changements hors scope ;
- une relance automatique unique si la première tentative ne laisse aucune modification autorisée ;
- reconstruction du `task-report.json` depuis l'état courant après correction ;
- possibilité d'ajouter un guidage de superviseur sans remplacer les contrats backlog.

### 5. Couche `integrate-task`

`autodev/src/autodev/integrate_task.py` n'intègre qu'une tâche `APPROVED`.

Comportements structurants déjà réutilisables :

- refus si le dépôt principal ou le worktree de tâche sont sales ;
- validation `TASK` avant merge dans le worktree ;
- baseline `FULL` sur la branche cible avant merge ;
- merge temporaire `--no-commit` ;
- validation `TASK` puis `FULL` après merge temporaire ;
- comparaison baseline/post-merge pour distinguer régression nouvelle, amélioration, panne d'environnement et échecs persistants ;
- rollback automatique limité aux cas sûrs ;
- nettoyage du worktree uniquement après intégration réussie.

Écart à combler côté produit :

- l'intégration de feature doit reprendre ce modèle de manière transactionnelle, mais au niveau branche produit complète : baseline avant fusion, merge temporaire sans commit, validations feature puis validations globales produit sur l'état fusionné, commit seulement si toutes les portes passent, rollback borné et preuve d'ancêtre après commit.

### 6. Couche `run-feature` et LangGraph

`autodev/src/autodev/run_feature.py` est le vrai graphe déterministe en production côté Autodev.

Caractéristiques :

- LangGraph avec checkpoint SQLite `.autodev/state/checkpoints.sqlite` ;
- état de feature explicite : backlog, tâche courante, tâches complétées/restantes, nombre de corrections, dernier verdict, statut, erreur, compteur de transitions ;
- reprise `--resume` basée sur l'état checkpointé et sur l'inspection Git réelle ;
- sélection séquentielle de la prochaine tâche prête ;
- arrêt sur `FAILED`, `HUMAN_REVIEW_REQUIRED`, `INTERRUPTED` ;
- détection de cycle de sélection et plafond de transitions ;
- décision de reprise `IMPLEMENT` / `REVIEW` / `CORRECT` / `INTEGRATE` / `HUMAN_REVIEW` / `INVALID_STATE`.

Limite majeure :

- le graphe ne sait gérer qu'une seule feature à la fois.

### 7. Checkpoints, états déterministes et monitoring

Les composants utiles sont déjà présents :

- checkpoint SQLite LangGraph pour `run-feature` ;
- artefacts `.autodev/runs/<task_id>/...` et `.autodev/runs/features/<feature_id>/...` ;
- `autodev/src/autodev/feature_status.py` pour un statut synthétique de feature ;
- `autodev/src/autodev/monitor_state.py` et `autodev/src/autodev/monitor.py` pour la lecture déterministe de l'état courant ;
- heartbeat JSON pendant `IMPLEMENT` et `REVIEW`, interprété comme actif ou suspect.

Limites :

- pas de journal JSONL de décisions produit ;
- pas de notion native de pause programmée, attente jusqu'à une heure donnée ou reprise après fenêtre de quota ;
- pas d'état global multi-features ;
- pas de séparation formelle entre plan déclaratif et état d'exécution reconstruit ;
- pas de transitions produit crash-safe ni de clés d'idempotence ;
- pas de namespace stable par `product_run_id`, ni de checkpoint produit séparé du checkpoint LangGraph feature existant.

### 8. Validation des commandes

La validation de sécurité des commandes est centralisée dans `validate_command_safe`.

Règles actuelles :

- rejet des tokens `;`, `&&`, `||`, `>`, `>>`, `<`, `|`, `` ` ``, `$(` ;
- découpage via `shlex.split` ;
- timeout ajusté selon la commande ;
- rejet des validations trop larges ou des commandes qui installent des dépendances au niveau backlog.

Incident déjà couvert :

- le caractère `|` dans un argument cité est quand même refusé, car la règle est textuelle et non syntaxique.

### 9. Runners Claude et Codex

Dans `autodev/` :

- Claude est lancé par `run_claude_non_interactive` avec `--permission-mode bypassPermissions` et outils autorisés explicites ;
- Codex de revue est lancé en lecture seule avec `codex exec --ephemeral --sandbox read-only --output-schema`.

Dans `orchestrator/` :

- `orchestrator.runners.claude_runner.ClaudeRunner` et `orchestrator.runners.codex_runner.CodexRunner` encapsulent les binaires avec wrappers injectables ;
- `orchestrator.runners.qa_runner.QARunner` reste simplifié et ne reprend pas les règles riches de `review-task`.

Constat :

- les wrappers `orchestrator/` sont réutilisables comme façade basse couche, mais la politique métier robuste est aujourd'hui dans `autodev/`.
- aucune politique propriétaire de spécification n'existe encore pour distinguer `approved-only`, `draft` et `autonomous`, ni pour interdire strictement la planification d'une spécification non validée.
- la séparation cible des rôles est la suivante :
  - Claude agent d'implémentation : modifie uniquement les fichiers autorisés ; aucun `commit`, `amend`, `reset`, `rebase`, `merge`, `cherry-pick` ni mutation de référence Git.
  - Codex reviewer : produit un verdict structuré sur le commit et les preuves courantes.
  - Codex superviseur : produit un diagnostic structuré et propose des actions typées.
  - orchestrateur Python : applique la politique et exécute les actions autorisées.

### 10. Schémas JSON et contrats

Schémas utiles déjà présents :

- `autodev/schemas/backlog.schema.json`
- `autodev/schemas/review-result.schema.json`

Contrats structurants :

- backlog de feature versionné avec requirements, tâches, `allowed_paths`, validations, justifications ;
- verdict de revue fermé sur `APPROVED`, `CORRECTION_REQUIRED`, `HUMAN_REVIEW_REQUIRED` ;
- `task-report.json` déterministe vérifié contre le diff courant ;
- `integration-result.json`, `validation-results.json`, `comparison.json`, `heartbeat.json`.

Limites :

- aucun schéma de plan produit multi-features ;
- aucun registre versionné de décisions acquises ;
- aucune taxonomie fermée d'incidents produit ;
- aucun schéma de diagnostic Codex superviseur ;
- aucun journal d'orchestration append-only.

### 11. Tests existants

Couverture utile constatée :

- `autodev/tests/test_task_runner.py`
- `autodev/tests/test_review_task.py`
- `autodev/tests/test_correct_task.py`
- `autodev/tests/test_integrate_task.py`
- `autodev/tests/test_run_feature.py`
- `autodev/tests/test_validation_baseline.py`
- `autodev/tests/test_monitor.py`
- `tests/unit/orchestrator/*`

Incidents déjà couverts par les tests :

- faux succès Claude avec permissions ;
- rapport narratif obsolète contredisant le code courant ;
- restauration des changements hors scope ;
- dépassement du maximum de corrections ;
- reprise `run-feature --resume` ;
- worktree absent, branche absente ou état Git incohérent ;
- baseline/post-merge et validations transitoires ;
- heartbeat actif ou suspect ;
- refus de `git reset --hard` dans `correct-task`.

## composants réutilisables

- `autodev.task_runner` pour l'isolation Git, les prompts d'implémentation, la validation de commandes et les artefacts de run.
- `autodev.review_task` comme moteur de revue structurée et de consolidation des preuves.
- `autodev.correct_task` comme boucle de correction supervisable et non destructive.
- `autodev.integrate_task` comme porte d'intégration finale conditionnée par `APPROVED`, `TASK PASS`, `FULL PASS` ou `PASS_WITH_BASELINE_FAILURES`.
- `autodev.run_feature` comme `FeatureGraph` existant.
- `autodev.process_runner` pour timeouts, heartbeat et arrêt de groupe de processus.
- `autodev.validation_baseline` pour comparer les validations transitoires et distinguer régression vs bruit d'environnement.
- `autodev.git_context`, `autodev.task_report`, `autodev.feature_status`, `autodev.monitor_state` pour la lecture d'état déterministe.
- `orchestrator.storage.task_store` et les wrappers runners de `orchestrator/` comme briques secondaires si un plan produit séparé doit être sérialisé.

## incidents observés : classement, composants concernés et insuffisances

### 1. Incidents fournisseur et quotas temporaires

- **Incidents couverts** : quota Claude, limite de session, indisponibilité temporaire, reprise différée.
- **Fonctions concernées** :
  - `autodev.task_runner.run_task`
  - `autodev.correct_task.correct_task`
  - `autodev.process_runner.run_process_capturing_timeout`
  - `autodev.monitor_state.read_heartbeat`
  - `autodev.run_feature.run_feature`
- **Insuffisances actuelles** :
  - aucun parseur d'heure/date de renouvellement ;
  - aucun état `WAITING_PROVIDER_RESET` ;
  - aucune distinction forte entre fournisseur Claude et fournisseur Codex ;
  - un incident quota finit aujourd'hui dans les voies d'échec ou d'interruption génériques.
- **Composants réutilisables** :
  - heartbeat et monitoring existants ;
  - journalisation des stdout/stderr Claude/Codex ;
  - mécanisme de reprise `run-feature --resume`.

### 2. Réconciliation Git après interruption, hooks et worktree partiel

- **Incidents couverts** : worktree partiel après interruption, mutation hook `AGENTS.md`, reprise cumulative.
- **Fonctions concernées** :
  - `autodev.correct_task.correct_task`
  - `autodev.correct_task.run_correction_attempt`
  - `autodev.git_context.build_current_task_git_state`
  - `autodev.git_tools.changed_paths_since`
  - `autodev.git_tools.dirty_paths`
  - `autodev.git_tools.git_status_porcelain`
  - `autodev.git_tools.git_status_with_branch`
- **Insuffisances actuelles** :
  - capture avant/après trop pauvre pour attribuer un changement à un hook, à l'agent ou à une mutation externe ;
  - comparaison essentiellement par chemins, pas par contenu ;
  - absence d'empreintes index/worktree/untracked ;
  - absence d'inventaire systématique des patchs produits par tentative ;
  - impossibilité d'expliquer de façon vérifiable pourquoi un fichier a été restauré ou conservé.
- **Composants réutilisables** :
  - artefacts `before-status.txt`, `modified-paths.json`, `out-of-scope-paths.json`, `restored-paths.json` ;
  - `git_context` pour récupérer une vue consolidée ;
  - logique de restauration sélective déjà présente dans `correct-task`.

### 3. Mutations Git agent interdites

- **Incidents couverts** : commit/amend/reset par l'agent, divergence d'historique, récupération bornée.
- **Fonctions concernées** :
  - `autodev.correct_task.correct_task`
  - `autodev.git_tools.amend_head_commit`
  - `autodev.git_tools.create_commit`
  - `autodev.integrate_task.integrate_task`
  - `autodev.run_feature.determine_task_resume_action`
- **Insuffisances actuelles** :
  - `correct-task` committe lui-même en fin de correction, mais ne capture pas de reflog avant/après l'exécution Claude ;
  - aucun contrôle structuré de `HEAD`, refs et reflog autour du runner agent ;
  - aucune récupération documentée des commits utiles créés illégalement par un agent.
- **Composants réutilisables** :
  - helpers Git existants ;
  - contrôle d'intégration transactionnelle déjà strict dans `integrate-task`.

### 4. Artefacts techniques stale et rapports narratifs contradictoires

- **Incidents couverts** : `task-report.json` périmé, `review-result.json` contradictoire, récit ancien factuellement faux.
- **Fonctions concernées** :
  - `autodev.task_report.verify_task_report`
  - `autodev.task_report.write_task_report`
  - `autodev.review_task.review_task`
  - `autodev.integrate_task.integrate_task`
  - `autodev.validation_baseline.compare_validation_results`
- **Insuffisances actuelles** :
  - `verify_task_report` compare des structures simples mais n'archive pas l'artefact stale ;
  - aucune empreinte explicite de diff ou de validations ;
  - pas de régénération idempotente de `review-result.json` ou de `current-paths.json` à l'échelle superviseur ;
  - pas de règle formelle séparant rapport narratif et artefact technique dans l'orchestration produit.
- **Composants réutilisables** :
  - vérification déjà robuste du `task-report.json` ;
  - relance déterministe des validations et lecture du diff courant dans `review-task` ;
  - comparaison baseline/post-merge déjà structurée.

### 5. Critères impossibles dans leur scope et extensions minimales de périmètre

- **Incidents couverts** : critère owned par la mauvaise tâche, besoin exact sur `plot_repo.rs`, besoin exact sur `dto/plot.rs`, fix mécanique hors scope sur `ParametresPage.tsx`.
- **Fonctions concernées** :
  - `autodev.acceptance_criteria.owned_criteria_by_task`
  - `autodev.planner.validate_backlog_consistency`
  - `autodev.task_runner.ensure_paths_allowed`
  - `autodev.task_runner.ensure_dependency_changes_allowed`
  - `autodev.validation_baseline.run_validation_set`
- **Insuffisances actuelles** :
  - validation backlog centrée sur la cohérence de structure, pas sur la faisabilité technique réelle par task owner ;
  - aucune comparaison baseline-vs-tentative pour distinguer défaut préexistant et régression ;
  - aucune procédure versionnée de réattribution ou d'extension exacte de scope ;
  - aucune règle imposant qu'une extension ou une réattribution reste explicite, bornée, mécanique, auditée et autorisée par politique avant application ;
  - absence de distinction entre décision mécanique bornée et décision métier.
- **Composants réutilisables** :
  - mapping requirement/task déjà existant ;
  - contrôles actuels de `allowed_paths` ;
  - baseline de validations réutilisable pour classer un défaut comme préexistant ou nouveau.

### 6. Corrections cumulatives et non-régression des acquis

- **Incidents couverts** : FP004-T02 avec sept corrections, régressions en chaîne, distinction plafond ordinaire/supervisé.
- **Fonctions concernées** :
  - `autodev.run_feature.node_decide_review`
  - `autodev.run_feature.node_correct_task`
  - `autodev.correct_task.build_correction_prompt`
  - `autodev.review_task.review_task`
  - `autodev.acceptance_criteria`
- **Insuffisances actuelles** :
  - pas de registre explicite des acquis validés à préserver ;
  - pas de contrôle structuré qu'un critère déjà `PASS` ne repasse pas `FAIL` ;
  - pas de budget supervisé séparé au-dessus du plafond ordinaire `run-feature`.
- **Composants réutilisables** :
  - séquence implement/review/correct/integrate existante ;
  - preuves requirement/acceptance déjà présentes dans les sorties de revue.

### 7. Validations sûres et ressources transitoires locales

- **Incidents couverts** : `rg` avec pipe littéral refusé à tort, `env PYTHONPATH=autodev/src pytest`, conflit de port Vite/Playwright.
- **Fonctions concernées** :
  - `autodev.task_runner.validate_command_safe`
  - `autodev.validation_baseline.run_validation_set`
  - `autodev.validation_baseline.compare_validation_results`
  - `autodev.integrate_task.integrate_task`
- **Insuffisances actuelles** :
  - validation textuelle par sous-chaînes interdites dans `FORBIDDEN_COMMAND_TOKENS` ;
  - aucune modélisation des préfixes d'environnement sûrs ;
  - aucune identification formelle des ports/processus locaux d'un worktree.
- **Composants réutilisables** :
  - exécution déjà sans shell ;
  - classification baseline/post-merge déjà apte à distinguer certaines erreurs d'environnement.

### 8. Persistance durable, multi-feature et points d'arrêt humains

- **Incidents couverts** : backlog ignoré par Git, décisions non durables, autonomie multi-feature, arrêt humain si ambiguïté.
- **Fonctions concernées** :
  - `autodev.run_feature.run_feature`
  - `autodev.monitor_state.read_feature_state`
  - `autodev.feature_status`
  - `autodev.cli`
- **Insuffisances actuelles** :
  - aucun `ProductGraph` ;
  - pas de source persistée pour les décisions de scope/ownership au-delà des artefacts éphémères ;
  - pas de sélection déterministe de la prochaine feature ni de dépendances produit globales.
- **Composants réutilisables** :
  - état et monitoring feature existants ;
  - checkpoint LangGraph et artefacts `.autodev/runs/features/`.

## décisions purement mécaniques vs décisions métier

### Décisions purement mécaniques

- parser une heure de reset fournisseur avec timezone explicite ;
- calculer un `retry_at` ou un backoff borné ;
- comparer des empreintes de contenu avant/après ;
- régénérer un artefact technique stale depuis diff et validations courants ;
- classer un échec de validation comme identique à la baseline ou comme nouvelle régression ;
- proposer une extension de scope exacte à un fichier pour une correction mécanique bloquante ;
- proposer une réattribution de critère vers une unique tâche réellement capable lorsqu'aucune ambiguïté métier ni concurrente n'existe ;
- rejouer une validation après conflit transitoire de port dûment identifié ;
- reprendre une feature après crash si l'état reconstruit est non ambigu.

### Décisions métier ou nécessitant validation humaine

- accepter une ambiguïté de spécification produit ;
- réattribuer un critère si plusieurs tâches propriétaires restent plausibles ;
- étendre le périmètre pour une modification fonctionnelle et non purement mécanique ;
- appliquer une extension ou une réattribution lorsque la politique ne l'autorise pas explicitement ;
- choisir entre deux interprétations concurrentes d'un même critère ;
- intégrer une feature quand une validation obligatoire reste contournée ou incertaine ;
- trancher une divergence Git dont l'attribution ne peut pas être prouvée ;
- décider d'abandonner l'attente fournisseur lorsqu'aucune borne fiable n'existe.

## points d'insertion concrets du ProductGraph

### 1. Entrée produit

- nouvelle commande CLI `autodev run-product PLAN` ;
- chargement d'un plan produit versionné distinct du backlog feature ;
- création d'un `product_run_id` et d'un namespace stable sous `.autodev/runs/products/<run_id>/`.

### 2. Sélection de feature

- lecture du plan produit global ;
- reconstruction des features déjà intégrées via Git et artefacts de feature ;
- sélection stable par dépendances, priorité puis identifiant.

### 3. Préparation de feature

- validation de la politique `approved-only` / `draft` / `autonomous` ;
- génération ou validation de spécification ;
- appel à `autodev plan` et audit de couverture ;
- audit de faisabilité des critères et du scope avant tout lancement agent.

### 4. Exécution et supervision

- encapsulation de `autodev.run_feature.run_feature` comme `FeatureGraph` exécutable ;
- interception des incidents structurés issus de `run-task`, `review-task`, `correct-task`, `integrate-task` ;
- appel éventuel au diagnostic Codex superviseur puis passage obligé par le moteur de politique.

### 5. Réconciliation et reprise

- capture Git avant hook, après hook et après agent ;
- inventaire des patchs et décisions de préservation ;
- reprise idempotente par action typée `RESUME_FEATURE`, `WAIT_PROVIDER_RESET`, `REGENERATE_TASK_REPORT`, `RECOVER_AGENT_GIT_HISTORY`.

### 6. Intégration transactionnelle de feature

- baseline produit ;
- merge temporaire sans commit sur branche produit ;
- validations feature puis produit ;
- commit d'intégration uniquement après `APPROVED`, `TESTS PASS`, `SCOPE PASS` et non-régression.

### 7. Clôture produit

- génération du rapport final produit à partir des preuves ;
- passage automatique à la feature suivante ;
- arrêt seulement si toutes les features requises sont intégrées ou si un arrêt humain est imposé.

## couplages actuels au niveau feature

- La source de vérité opérationnelle d'une tâche est répartie entre Git, `.autodev/runs/<task_id>/`, le backlog JSON et le checkpoint de feature.
- `run-feature` suppose qu'un backlog représente exactement une feature.
- La sélection de la tâche prête dépend de l'ordre dans le backlog et du statut d'intégration des dépendances, pas d'une priorité produit globale.
- Les artefacts de correction, revue et intégration sont tous indexés par `task_id`, pas par run produit.
- Le contenu de `SPEC.md` est injecté dans `run-task`, ce qui couple fortement l'exécution à la spécification courante du dépôt.
- `review-task` et `correct-task` dépendent du fait que les preuves héritées existent déjà dans `.autodev/runs/` pour les dépendances intégrées.

## risques de concurrence entre deux workflows

- aucun workflow concurrent ne doit pouvoir exécuter ou reprendre la même feature ;
- collision sur `.autodev/state/checkpoints.sqlite` si plusieurs graphes écrivent sans coordination globale ;
- collision sur `.autodev/worktrees/<task_id>` si deux superviseurs choisissent la même tâche ;
- concurrence entre une intégration en cours et un autre workflow qui salit la branche cible ;
- concurrence sur les artefacts `.autodev/runs/<task_id>/...` si une tâche est relancée pendant qu'une autre session analyse les mêmes fichiers ;
- absence de verrou produit empêchant deux `run-feature` de choisir des features incompatibles ou partageant des chemins sensibles ;
- absence de verrou de feature et de protocole audité de récupération d'un verrou périmé ;
- absence de namespace stable par `product_run_id` pour rattacher séparément état, checkpoints, journaux et artefacts enfant ;
- absence d'identifiants LangGraph distincts produit/feature pour éviter le mélange d'exécutions ;
- absence de verrous contenant identité du run, PID ou heartbeat et propriétaire logique ;
- absence de règle d'exclusion empêchant deux plans partageant le même `feature_id` ou `task_id` d'écrire dans les mêmes artefacts ;
- absence d'état global pour empêcher qu'une feature B parte alors que la feature A n'a pas encore stabilisé une décision structurante partagée ;
- aucune attente native en cas de limite de session Claude, de quota ou de fenêtre horaire de reprise.
- absence de politique distincte pour sérialiser Claude lorsque plusieurs workflows partagent le même compte ou le même quota fournisseur ;
- absence de garde-fou explicite contre une double reprise, une double intégration ou une clôture concurrente ;
- `monitor` et `product-status` devront rester strictement non mutateurs.

## lacunes empêchant un ProductGraph

- pas de plan produit versionné décrivant features, dépendances, priorité, blocages, fenêtre d'exécution et politique ;
- pas de sélection déterministe de la prochaine feature ;
- pas d'état global multi-features ;
- pas de taxonomie formelle d'incidents ;
- pas de registre persistant des décisions acquises à préserver ;
- pas de moteur de politique séparant règles automatiques et arrêts humains obligatoires ;
- pas de liste fermée des actions automatiques au niveau produit ;
- pas de journal JSONL append-only pour audit produit ;
- pas de collecteur de preuves autoritatives ni de diagnostic Codex structuré séparant faits, inférences, contraintes, action et confiance ;
- pas de séparation explicite entre le rôle Codex reviewer et le rôle Codex superviseur ;
- pas de support pause/reprise différée par date ou par événement externe ;
- pas de reprise idempotente garantissant l'absence de double intégration ou de double correction après crash ;
- pas de capture Git avant processus et après initialisation pour détecter les mutations de hooks ;
- pas de capture Git assez précise pour distinguer l'état dirty préexistant, le delta hors scope attribuable au run courant et les mutations de hooks ;
- pas de règle interdisant explicitement toute restauration d'une modification préexistante ambiguë ;
- pas de stratégie de worktrees multi-features avec verrous produit et feature ;
- pas de politique de génération des spécifications manquantes avec traçabilité source/prompt/commit/statut de validation ;
- pas de garde-fou interdisant toute planification sur une spécification non validée ;
- pas de cycle produit couvrant génération/validation de spécification, `autodev plan`, couverture à 100 %, finalisation et intégration de feature ;
- pas de validation de la baseline produit ni de preuve que le commit de feature intégré est ancêtre de la branche produit ;
- pas de tests de collision entre deux runs concurrents ;
- pas de clôture produit dérivée des preuves ni de rapport final produit structuré ;
- la couche `orchestrator/` n'exploite pas encore les invariants riches d'`autodev`.

## stratégie de tests progressive attendue pour le superviseur

### Niveau 1 — Unit tests purs

- parseur d'incidents fournisseur et de timezone ;
- empreintes de contenu index/worktree/untracked ;
- validation lexicale des commandes ;
- calcul d'idempotence et de backoff ;
- détection d'artefact stale par empreintes ;
- décision de scope extension vs réattribution vs arrêt humain.

### Niveau 2 — Intégration Git locale

- worktree partiel après interruption ;
- même chemin avant/après mais contenu différent ;
- hook `AGENTS.md` entre capture pré-hook et post-hook ;
- commit/amend/reset réalisés par l'agent ;
- baseline `ParametresPage.tsx` vs tentative corrigée ;
- retry Vite/Playwright avec conflit de port identifié.

### Niveau 3 — Intégration FeatureGraph

- plafond ordinaire puis corrections supervisées de type FP004-T02 ;
- artefacts stale régénérés avant revue ;
- reprise idempotente après crash ;
- décisions acquises réinjectées dans la correction.

### Niveau 4 — E2E ProductGraph

- deux features successives avec dépendance satisfaite ;
- arrêt humain sur ambiguïté produit ;
- absence de double reprise et de double intégration ;

## stratégie d'atomisation complète attendue

Chaque exigence `R1` à `R29` doit avoir exactement une tâche propriétaire capable de la mettre en œuvre. Le nombre de tâches n'a pas besoin de refléter le nombre d'exigences, mais aucune exigence ne doit être omise et aucune tâche ne doit recevoir un scope irréaliste.

Lots d'implémentation cohérents attendus :

1. plan produit et schéma versionné ;
   exigences couvertes : `R1` ;
   scope réaliste : modules de plan produit et schémas JSON versionnés, avec leurs tests.
2. politique des spécifications ;
   exigences couvertes : `R20` ;
   scope réaliste : modules de politique `approved-only` / `draft` / `autonomous`, validation et tests dédiés.
3. état produit, reconstruction et persistance durable ;
   exigences couvertes : `R2`, `R29.1` à `R29.3` ;
   scope réaliste : modules d'état produit, stockage runtime et tests de reconstruction.
4. sélection de feature et dépendances Git ;
   exigences couvertes : `R4` ;
   scope réaliste : modules de sélection produit, `git_context`, `git_tools` et tests Git.
5. taxonomie des incidents ;
   exigences couvertes : `R6` ;
   scope réaliste : schémas d'incidents, enums, validation et tests de contrat.
6. diagnostic Codex et collecteur de preuves ;
   exigences couvertes : `R7` ;
   scope réaliste : collecteur produit, schéma de diagnostic et tests de sérialisation.
7. registre des décisions acquises ;
   exigences couvertes : `R8`, `R28.1` ;
   scope réaliste : registre de décisions/acquis et tests de persistance.
8. politique déterministe et liste fermée des actions ;
   exigences couvertes : `R9`, `R12` ;
   scope réaliste : modules de politique produit, actions typées et tests d'autorisation.
9. runtime, namespaces, idempotence et verrous ;
   exigences couvertes : `R13` ;
   scope réaliste : `run_product.py`, stockage de run, verrous et tests de crash/reprise.
10. quotas fournisseur, retry_at, attente, pause et reprise ;
    exigences couvertes : `R14`, `R21` ;
    scope réaliste : runners Claude/Codex, orchestration de reprise, commandes CLI produit et tests d'attente.
11. snapshots Git complets, empreintes et attribution ;
    exigences couvertes : `R11`, `R22` ;
    scope réaliste : `git_tools`, `git_context`, `correct_task` et tests d'empreintes/réconciliation.
12. protection et récupération d'historique Git ;
    exigences couvertes : `R23` ;
    scope réaliste : runners agent, audit reflog, récupération bornée et tests d'intégration Git.
13. fraîcheur et régénération des artefacts ;
    exigences couvertes : `R24` ;
    scope réaliste : `review_task.py`, `task_report.py` et tests d'artefacts stale.
14. audit de faisabilité des critères ;
    exigences couvertes : `R25.1` à `R25.4` ;
    scope réaliste : planificateur/backlog et tests de faisabilité.
15. réattribution contrôlée des critères ;
    exigences couvertes : `R25.5` à `R25.9` ;
    scope réaliste : politique produit, backlog versionné et tests de réattribution.
16. baseline différentielle et extension minimale de scope ;
    exigences couvertes : `R26` ;
    scope réaliste : `validation_baseline.py`, `correct_task.py`, backlog et tests d'extension.
17. validation sécurisée et exécutable des commandes ;
    exigences couvertes : `R27.1` à `R27.5` ;
    scope réaliste : `task_runner.py` et ses tests.
18. incidents Vite/Playwright et ressources locales ;
    exigences couvertes : `R19.4`, `R27.6` à `R27.8` ;
    scope réaliste : `validation_baseline.py`, `integrate_task.py` et tests de retry local.
19. préparation de feature, exécution ProductGraph / FeatureGraph et corrections cumulatives ;
    exigences couvertes : `R3`, `R5`, `R10`, `R28.2` à `R28.8`, `R29.4`, `R29.5` ;
    scope réaliste : `run_feature.py`, `run_product.py`, modules superviseur et tests FP004.
20. intégration transactionnelle, clôture produit, CLI, monitoring et non-régression multi-feature ;
    exigences couvertes : `R16`, `R17`, `R18`, `R19`, `R29.6`, `R29.7` ;
    scope réaliste : `run_product.py`, `cli.py`, `monitor_state.py`, intégration produit et tests E2E.

## dépendances minimales de planification

1. plan produit et politique de spécification avant toute sélection ;
2. plan et état reconstruit avant sélection ;
3. taxonomie des incidents avant diagnostics ;
4. snapshots Git avant empreintes et attribution ;
5. empreintes avant réconciliation des fichiers déjà modifiés ;
6. registre des décisions acquises avant corrections cumulatives ;
7. politique et liste fermée des actions avant actions sensibles ;
8. quotas fournisseur avant reprise temporisée ;
9. snapshots Git avant récupération d'historique ;
10. faisabilité avant préparation ou exécution d'une feature ;
11. baseline avant extension de scope ;
12. artefacts frais avant revue ;
13. exécution avant intégration ;
14. intégration avant clôture ;
15. CLI et monitoring après disponibilité des composants utiles.

## règles de scope réaliste pour les tâches futures

- une tâche de réconciliation peut viser `correct_task.py` et ses tests si elle traite la réconciliation, pas un module produit sans lien ;
- une tâche de validation des commandes peut viser `task_runner.py` et ses tests, avec contrôle automatique préalable de tout le backlog ;
- une tâche d'artefacts stale peut viser `review_task.py`, `task_report.py` et leurs tests ;
- une tâche de quotas ou d'interdiction Git peut viser les runners Claude/Codex et les tests associés ;
- une tâche de reprise temporisée ou de plafonds peut viser `run_feature.py` et les tests de reprise ;
- une tâche de snapshots Git peut viser `git_tools.py`, `git_context.py` et les tests exacts de snapshots ;
- une tâche CLI produit peut viser `cli.py`, les commandes `run-product` / `resume-product` / `product-status` / `monitor-product` / `pause-product` et leurs tests ;
- les modules produit dédiés, les tests exacts et les rapports correspondants doivent être inclus lorsque nécessaires, sans ouvrir des chemins plus larges que l'exigence.

## validations exécutables

- les validations doivent être directement exécutables sans shell implicite ;
- `env PYTHONPATH=autodev/src pytest -q ...` est valide ;
- `PYTHONPATH=autodev/src pytest -q ...` ne doit jamais être émis comme `argv[0]` d'un processus lancé sans shell ;
- un contrôle automatique de toutes les commandes du backlog doit être exécuté avant lancement.

## clarification scope extension / arrêt humain

- une modification hors scope non autorisée reste interdite ;
- une extension de scope ne peut jamais être implicite ;
- `REQUEST_SCOPE_EXTENSION` produit une proposition structurée ;
- `APPLY_SCOPE_EXTENSION` n'est possible que si une politique explicite l'autorise ;
- l'extension doit viser un fichier précis, être justifiée, mécanique, bornée, auditée et sans ambiguïté métier ;
- `REQUEST_HUMAN` reste obligatoire si la politique ne l'autorise pas, si plusieurs solutions existent, si l'impact fonctionnel est ambigu ou si la sûreté Git ne peut être garantie ;
- la même logique s'applique à `REQUEST_CRITERION_REALLOCATION` et `APPLY_CRITERION_REALLOCATION`.
- persistance durable des décisions de scope/ownership ;
- clôture complète du produit sans double intégration.

## endroits où ajouter un superviseur structuré

### Couche recommandée

Ajouter le superviseur au-dessus d'`autodev.run_feature` et non à l'intérieur de `run-task` ou `review-task`.

### Points d'insertion concrets

- nouveau plan produit déclaratif versionné sous `.autodev/`, séparé de l'état reconstruit sous les runs produit ;
- nouveau `ProductGraph` Python avec son propre checkpoint, ses journaux JSONL et ses transitions idempotentes ;
- commandes CLI `run-product`, `product-status`, `monitor-product`, `pause-product` et `resume-product` ;
- appels du `ProductGraph` vers `run-feature`, puis observation déterministe via `feature_status` et `monitor_state` ;
- utilisation d'un registre de décisions et d'incidents que `correct-task` peut recevoir comme guidance de haut niveau ;
- collecteur de preuves et diagnostic Codex superviseur conforme à un schéma versionné ;
- moteur de politique et exécuteur limité à des actions typées ;
- adaptation de `run-feature` pour transférer au superviseur le plafond ordinaire de correction au lieu de conclure immédiatement à un arrêt humain.

## incidents réels et impact architectural

- `|` refusé dans un argument cité : la politique de validation de commandes doit devenir syntaxique ou catégorielle, pas seulement basée sur une sous-chaîne.
- rapports narratifs périmés : la preuve de décision doit être dérivée du Git courant et des artefacts structurés, jamais d'un texte libre seul.
- corrections successives régressives : un registre de décisions acquises doit alimenter les prompts de correction et les règles de non-régression.
- critères simultanés à réconcilier : la politique doit raisonner sur l'ensemble des checks propriétaires et non sur une seule issue isolée.
- dépassement du plafond ordinaire de corrections : `run-feature` doit enregistrer un incident et escalader au superviseur, qui peut autoriser des corrections supplémentaires dans un plafond supervisé distinct ; seul le plafond supervisé absolu impose un humain.
- FP004-T02 : le cas réel démontre que trois corrections ordinaires puis les corrections supervisées 4 à 7 peuvent aboutir à `APPROVED` ; un arrêt humain au premier plafond aurait été incorrect.
- limite de session Claude avec heure de réinitialisation : nécessité d'un état `WAITING_UNTIL` et d'une reprise programmée.
- spécification manquante ou non validée : nécessité d'une politique fermée `approved-only` / `draft` / `autonomous`, avec traçabilité complète et blocage de la planification tant que la validation n'est pas acquise.
- FP004-T03 : Claude retourne le code 1 pour limite de session et `correction-result` déclare `modified_paths` vide alors que quatre fichiers du worktree sont modifiés ; Git réel doit primer, les modifications autorisées doivent être conservées et un quota fournisseur ne doit pas consommer une correction métier.
- mutation au démarrage : un hook peut mettre à jour automatiquement le bloc `claude-mem` d'`AGENTS.md` ; une capture Git avant lancement et une autre après initialisation doivent distinguer cette mutation de celles du processus principal.
- worktree partiellement modifié après interruption : nécessité de classer les changements autorisés, partiels et hors scope, de préserver intégralement le dirty state préexistant, puis de ne restaurer de façon bornée et auditée que les chemins hors scope attribuables au run courant avant reprise depuis le commit et le worktree réels.
- validations Vite/Playwright transitoires : nécessité d'une classification environnementale et d'une politique de réessai bornée.
- collisions entre runs : nécessité de namespaces, checkpoints, identifiants LangGraph, artefacts et verrous isolés par `product_run_id`, avec tests dédiés.
- intégration seulement après `APPROVED`, `tests PASS` et `scope PASS` : ce contrat doit rester non négociable au niveau produit.

## décisions prises

- Le futur superviseur produit doit réutiliser `autodev` comme socle d'exécution et de preuve, et non repartir de `orchestrator/` seul.
- La bonne architecture cible est imbriquée : `ProductGraph -> FeatureGraph -> TaskGraph`, avec `run-feature` comme ancêtre direct du futur `FeatureGraph`.
- Le plan versionné porte l'intention ; l'état opérationnel est reconstruit depuis Git, les artefacts et les checkpoints puis persisté séparément sous le run produit.
- La politique de spécification doit devenir une exigence propriétaire distincte, avec trois modes fermés et interdiction absolue de planifier une spécification non validée.
- Les artefacts source de vérité doivent rester Git, schémas JSON structurés et journaux append-only ; les rapports narratifs ne doivent plus piloter les décisions.
- Le diagnostic Codex propose une action structurée mais seul le moteur déterministe peut l'autoriser ; aucune commande shell libre issue du modèle n'est exécutable.
- Les incidents réels doivent être modélisés explicitement dans une taxonomie fermée pour éviter les reprises implicites ou incohérentes.
- La stratégie de reprise doit inclure pause, attente programmée et audit de worktree avant toute relance automatique.
- Le dirty state préexistant du dépôt et des worktrees doit être traité comme intouchable sauf preuve stricte qu'un delta hors scope provient du run courant ; `AGENTS.md` doit être comparé avant hooks, après hooks et après processus.
- L'intégration de feature doit reprendre le contrat transactionnel d'`integrate-task` au niveau produit : baseline, merge temporaire sans commit, validations sur résultat fusionné, rollback borné et preuve d'ancêtre après commit.
- L'isolation inter-runs doit reposer sur un namespace stable par `product_run_id`, des checkpoints séparés, des identifiants LangGraph distincts et des verrous audités.
- Push, PR, merge distant et release restent hors automatisation V1.

## problèmes connus

- `AGENTS.md` renvoie vers `agents/STATUS.md`, mais le dépôt présent ne contient qu'un `STATUS.md` de redirection et pas le fichier cible.
- La couche `orchestrator/` actuelle et la couche `autodev/` se recouvrent partiellement sans source de vérité unifiée.
- L'inventaire repose sur les sources présentes dans ce worktree ; il ne vérifie pas d'éventuels artefacts externes absents du dépôt.
- Aucun test n'exerce encore un vrai `ProductGraph`, puisqu'il n'existe pas ; manquent notamment les E2E du cycle feature, FP004-T02, FP004-T03, crash/reprise, collisions entre deux runs et politique de spécification.

## résultats des tests

- Aucun test applicatif supplémentaire lancé dans cette étape documentaire, conformément à la consigne de ne pas implémenter de code.
- L'inspection a couvert le code source `autodev/`, `orchestrator/`, les schémas JSON, les rapports d'architecture existants et les tests unitaires/Autodev pertinents.
- `git diff --check` sera exécuté à la fin de la mission pour vérifier uniquement la propreté du diff créé.

## prochaine étape

Transmettre la spécification à `autodev plan`. L'atomisation attendue sépare plan/schéma, politique de spécification, état/réconciliation, sélection/dépendances, incidents, diagnostic Codex, décisions, politique/actions, journaux/namespace/verrous, attente/reprise, dirty state Git préexistant, génération/validation/planification, intégration transactionnelle de feature, CLI/monitoring et E2E/rapport final. Chaque critère doit avoir une seule tâche propriétaire, sans doublon de couverture.
