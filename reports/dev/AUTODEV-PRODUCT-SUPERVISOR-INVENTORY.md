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

## couplages actuels au niveau feature

- La source de vérité opérationnelle d'une tâche est répartie entre Git, `.autodev/runs/<task_id>/`, le backlog JSON et le checkpoint de feature.
- `run-feature` suppose qu'un backlog représente exactement une feature.
- La sélection de la tâche prête dépend de l'ordre dans le backlog et du statut d'intégration des dépendances, pas d'une priorité produit globale.
- Les artefacts de correction, revue et intégration sont tous indexés par `task_id`, pas par run produit.
- Le contenu de `SPEC.md` est injecté dans `run-task`, ce qui couple fortement l'exécution à la spécification courante du dépôt.
- `review-task` et `correct-task` dépendent du fait que les preuves héritées existent déjà dans `.autodev/runs/` pour les dépendances intégrées.

## risques de concurrence entre deux workflows

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
