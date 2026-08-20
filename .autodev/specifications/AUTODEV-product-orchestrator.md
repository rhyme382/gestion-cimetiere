# FEATURE-AUTODEV-PRODUCT-ORCHESTRATOR — Superviseur produit autonome Autodev

## Contexte

Autodev sait déjà ordonnancer une tâche (`run-task`, `review-task`, `correct-task`, `integrate-task`) et une feature (`run-feature`, checkpoints SQLite, preuves Git et validations déterministes). Il lui manque une couche produit qui sélectionne et conduit plusieurs features, réconcilie les interruptions avec l'état Git réel et n'escalade à un humain que lorsqu'une politique déterministe ne peut plus décider en sécurité.

Cette feature inclut l'implémentation du superviseur. Elle doit réutiliser les invariants existants sans affaiblir les portes `APPROVED`, `tests PASS` et `scope PASS`.

## Objectif utilisateur

En tant que superviseur produit Autodev, je peux exécuter ou reprendre un plan produit versionné jusqu'à sa clôture, avec des décisions déterministes, des preuves structurées, une isolation Git contrôlée et des arrêts humains explicites.

## Périmètre

- implémentation Python du `ProductGraph` ;
- réutilisation ou encapsulation du `FeatureGraph` et du `TaskGraph` existants ;
- diagnostic Codex structuré et séparation des rôles reviewer/superviseur ;
- collecteur d'artefacts et de preuves autoritatifs ;
- taxonomie fermée des incidents et registre des décisions acquises ;
- moteur de politique déterministe et exécuteur d'actions contrôlé ;
- schémas JSON versionnés, checkpoints et journaux JSONL append-only ;
- stratégie Git, branches, worktrees et verrous produit/feature ;
- cycle complet de génération, planification, exécution, validation et intégration d'une feature ;
- état produit reconstruit et persisté séparément du plan déclaratif ;
- CLI `run-product`, `product-status`, `monitor-product`, `pause-product`, `resume-product` ;
- tests unitaires, d'intégration et E2E Autodev ;
- rapport final de feature et rapport final produit dérivés des preuves.

## Hors périmètre

- modification du produit Rust, React ou Tauri ;
- orchestration parallèle réelle des features dans la V1 ;
- push, fusion de PR distante et release automatiques ;
- opérations destructives non bornées.

## Exigences fonctionnelles

### R1 — Plan produit déclaratif et schéma versionné

Le plan produit versionné décrit l'intention, jamais l'état opérationnel faisant foi.

Critères d'acceptation :

1. Un schéma JSON versionné impose `schema_version`, identifiant, date de génération, branche d'intégration produit, features, dépendances, priorités, caractère obligatoire ou optionnel de chaque feature, chemins de spécifications, validations de feature, validations globales produit et politique de spécification.
2. Les identifiants dupliqués, dépendances inconnues, cycles et versions inconnues sont rejetés.
3. Tout statut mutable éventuellement présent dans un plan est informatif et n'est jamais accepté comme état courant sans réconciliation.
4. Le plan est immuable pendant un run ; toute révision est identifiée et auditée.

### R20 — Politique de spécification propriétaire

La gestion d'une spécification suit une politique propriétaire explicite, traçable et bloquante pour toute planification.

Critères d'acceptation :

1. La politique supporte exactement `approved-only`, `draft` et `autonomous`.
2. `approved-only` exige une spécification préexistante et validée avant toute planification de feature.
3. `draft` génère un brouillon traçable, conforme au format propriétaire d'exigences et critères, puis impose `REQUEST_HUMAN` tant que la validation humaine n'est pas acquise.
4. `autonomous` génère une spécification traçable, la valide par contrat structuré conforme au format propriétaire, puis peut autoriser la suite uniquement si la politique du plan l'autorise et qu'aucune ambiguïté métier n'existe.
5. Toute spécification générée ou réutilisée trace au minimum sa source, le prompt ou l'origine documentaire, le commit de rattachement et son statut de validation.
6. Aucune planification, aucun backlog et aucune exécution de feature ne sont autorisés à partir d'une spécification non validée.
7. Toute ambiguïté métier, contradiction produit ou divergence entre exigences impose `REQUEST_HUMAN`.

### R2 — État d'exécution reconstruit et séparé

L'état courant est persisté sous le run produit et reconstruit depuis les artefacts structurés, Git et les checkpoints.

Critères d'acceptation :

1. Chaque run possède un état séparé du plan, sous `.autodev/runs/products/<run_id>/`.
2. La reconstruction compare plan, état persisté, checkpoints, branches, commits, worktrees, validations et artefacts enfants.
3. Une divergence de statut, de commit de base, de commit intégré, de dépendance ou d'artefact obligatoire produit un incident typé.
4. `REBUILD_STATUS` ne marque jamais une feature terminée sur la seule foi d'un champ du plan ou d'un rapport narratif.

### R3 — Architecture imbriquée

Le système implémente `ProductGraph -> FeatureGraph -> TaskGraph`.

Critères d'acceptation :

1. `ProductGraph` pilote les transitions produit et encapsule ou invoque le `FeatureGraph` compatible avec `run-feature`.
2. `FeatureGraph` conduit une feature complète et `TaskGraph` conserve `run-task -> review-task -> correct-task -> integrate-task`.
3. Les entrées, sorties, responsabilités et états persistés des trois niveaux sont distincts.
4. Un niveau parent ne peut contredire une preuve autoritative d'un niveau enfant.

### R4 — Sélection et dépendances

La prochaine feature est sélectionnée de manière stable parmi celles dont les dépendances sont réellement intégrées.

Critères d'acceptation :

1. L'ordre est déterminé par dépendances, priorité, puis identifiant stable.
2. Une feature dépendante part d'une base produit dont l'historique contient les commits intégrés de toutes ses dépendances.
3. La présence de ces commits est vérifiée par relation d'ancêtre Git, pas par statut déclaré.
4. Une incohérence produit un incident ; une feature terminée n'est pas relancée.

### R5 — Cycle complet d'une feature

Le `ProductGraph` exécute séquentiellement le cycle suivant.

Critères d'acceptation :

1. Il vérifie les dépendances puis sélectionne la feature.
2. Il vérifie ou génère sa spécification selon la politique, puis la valide.
3. Il crée branche et worktree de feature depuis la base produit courante.
4. Il lance `autodev plan` et exige une couverture propriétaire de 100 %.
5. Il supervise toutes les tâches jusqu'à ce qu'elles soient toutes `APPROVED` et `INTEGRATED`.
6. Il génère et vérifie le rapport final de feature depuis les preuves.
7. Il exécute les validations de feature et la baseline globale produit.
8. Il intègre la feature dans la branche produit et vérifie que le commit intégré en est ancêtre.
9. Il marque la feature terminée uniquement depuis ces preuves, puis sélectionne la suivante.

### R6 — Taxonomie fermée des incidents

Tout écart devient un incident structuré.

Critères d'acceptation :

1. Chaque incident a un code stable, une sévérité, un périmètre, des preuves, une répétabilité et une action recommandée.
2. La taxonomie couvre quotas fournisseur, permissions, état Git divergent, mutation d'initialisation, worktree interrompu ou sale non déclaré, validations transitoires, plafonds de correction ordinaire et supervisé, dépendance ou spécification manquante, conflit Git et décision humaine.
3. Les codes sont uniques et fermés par schéma versionné.
4. Tout incident précise s'il est réessayable, différable, corrigible sous supervision ou terminal.

### R7 — Diagnostic Codex structuré

Un Codex superviseur produit diagnostique à partir d'un dossier de preuves courant, distinct du Codex reviewer d'une tâche.

Critères d'acceptation :

1. Un collecteur réunit le commit, le diff, l'état Git, les validations, la revue, les corrections antérieures, les incidents et les décisions acquises.
2. La collecte est refaite immédiatement avant chaque diagnostic ; les artefacts autoritatifs courants priment sur les narratifs.
3. La sortie respecte un schéma JSON versionné séparant faits, inférences, contraintes à préserver, action proposée et niveau de confiance.
4. Le reviewer décide de la conformité d'une tâche ; le superviseur diagnostique un incident et propose une action sans remplacer le verdict de revue.
5. Aucune commande shell libre produite par un modèle n'est exécutée directement.
6. Toute proposition est validée par le moteur de politique déterministe puis traduite en une action de la liste fermée.

### R8 — Registre des décisions acquises

Les corrections préservent les décisions déjà validées.

Critères d'acceptation :

1. Une décision possède identifiant, périmètre, énoncé, preuves, statut et historique.
2. Elle est rattachable à un produit, une feature, une tâche, une exigence ou un incident.
3. Toute correction reçoit les décisions pertinentes comme contraintes à préserver.
4. Seul un événement structuré et justifié peut invalider une décision ; Git et verdicts structurés priment sur le narratif.

### R9 — Moteur de politique et exécuteur contrôlé

Les faits, propositions et décisions d'exécution sont séparés.

Critères d'acceptation :

1. À entrée identique, la politique choisit la même action autorisée.
2. Chaque proposition est contrôlée quant au scope, aux préconditions, aux plafonds et aux décisions acquises.
3. L'exécuteur n'accepte que des paramètres typés et des opérations préimplémentées ; il refuse commandes libres et actions inconnues.
4. Aucun chemin ne contourne `APPROVED`, `tests PASS`, `scope PASS` ou la baseline produit.

### R10 — Deux plafonds de correction

Le plafond ordinaire de `run-feature` est une escalade au superviseur, pas un arrêt humain automatique.

Critères d'acceptation :

1. Son dépassement produit un incident structuré `ORDINARY_CORRECTION_LIMIT_REACHED` transmis au superviseur.
2. Le superviseur peut lancer une correction supplémentaire si les problèmes sont déterminés, le périmètre autorisé, sans ambiguïté métier, et si les décisions acquises sont préservables.
3. Ces corrections consomment un compteur supervisé distinct et borné.
4. Seul le dépassement du plafond supervisé absolu impose `REQUEST_HUMAN`.
5. Un test reproduit FP004-T02 : corrections ordinaires 1 à 3, supervisées 4 à 7, puis verdict final `APPROVED`.

### R11 — Réconciliation après interruption

Toute interruption est réconciliée avec le worktree réel avant reprise.

Critères d'acceptation :

1. L'état Git est capturé avant lancement, après initialisation du processus et à sa terminaison.
2. La comparaison détecte une mutation de hook au démarrage, notamment le bloc `claude-mem` d'`AGENTS.md`.
3. L'état Git réel est comparé aux `modified_paths` déclarés et les modifications sont classées autorisées, partielles ou hors scope.
4. Les modifications autorisées sont conservées ; seuls les chemins hors scope sont restaurés de façon bornée et auditée.
5. Un diagnostic structuré précède toute reprise, laquelle repart du commit et du worktree réels.
6. Un quota ou une limite de session fournisseur ne consomme pas une correction métier.
7. Un test reproduit FP004-T03 : Claude code 1, `modified_paths` vide, quatre fichiers réellement modifiés et préservés s'ils sont autorisés.
8. L'état Git initial est capturé avec assez de précision pour distinguer les modifications, index, fichiers non suivis et métadonnées de branche préexistants de ceux produits par la tentative courante.
9. Aucune restauration, aucun écrasement ni aucune normalisation ne peuvent toucher une modification préexistante au lancement.
10. Seul un delta hors scope attribuable de manière prouvée à la tentative courante peut être restauré.
11. Toute restauration est précédée d'une sauvegarde par patch, diff ou preuve structurée suffisante pour audit et éventuelle reconstitution.
12. Si l'attribution d'un changement au processus courant est ambiguë, la reprise automatique est interdite et `REQUEST_HUMAN` est imposé.
13. Le cas `AGENTS.md` compare explicitement la version avant processus, après hooks d'initialisation et après processus afin de distinguer mutation de hook, modification du run et état préexistant.

### R12 — Liste fermée des actions

Les seules actions automatiques V1 sont celles du tableau suivant.

| Action | Préconditions | Effets | Artefacts modifiables | Incidents possibles |
|---|---|---|---|---|
| `GENERATE_SPECIFICATION` | politique autorisante, feature sélectionnée | crée une spécification traçable | spécification, journal | génération invalide, scope interdit |
| `VALIDATE_SPECIFICATION` | spécification présente | valide ou bloque | validation, incident, journal | schéma ou contenu invalide |
| `CREATE_FEATURE_BRANCH` | base propre et dépendances intégrées | crée branche/worktree | Git, registre worktrees, journal | collision, base divergente |
| `PLAN_FEATURE` | spécification valide, worktree prêt | lance `autodev plan` | backlog et artefacts de plan | échec outil, plan invalide |
| `VALIDATE_PLAN_COVERAGE` | plan présent | calcule la couverture propriétaire | rapport de couverture | couverture incomplète |
| `SELECT_FEATURE` | état réconcilié | désigne une feature éligible | état, journal | dépendance incohérente |
| `RUN_FEATURE` | couverture 100 %, verrous acquis | démarre le FeatureGraph | checkpoints et artefacts enfant | interruption, validation, quota |
| `RESUME_FEATURE` | diagnostic et réconciliation terminés | reprend sans doublon | checkpoints, journal | état incompatible |
| `RETRY_VALIDATION` | incident réessayable, quota disponible | rejoue une validation | résultat de validation | échec persistant |
| `RETRY_REVIEW` | revue réessayable | rejoue la revue | résultat de revue | sortie invalide, quota |
| `REQUEST_CORRECTION` | verdict correction, plafond ordinaire disponible | lance une correction métier | artefacts de correction | scope, plafond atteint |
| `RUN_SUPERVISED_CORRECTION` | critères R10 satisfaits | lance une correction supervisée | correction, décisions, compteurs | plafond absolu, régression |
| `WAIT_UNTIL` | échéance explicite | persiste l'attente sans bloquer | état, checkpoint, journal | date invalide |
| `RECONCILE_WORKTREE` | interruption ou divergence | classe et réconcilie les modifications | audit et restauration hors scope | conflit, modification ambiguë |
| `INTEGRATE_APPROVED_TASK` | tâche approved, tests/scope pass | intègre une tâche une fois | Git, résultat d'intégration | baseline, conflit |
| `FINALIZE_FEATURE` | tâches intégrées | génère/vérifie le rapport feature | rapport et preuves | rapport incohérent |
| `VALIDATE_PRODUCT_BASELINE` | feature finalisée | vérifie la non-régression | résultats de validation | régression, bruit persistant |
| `INTEGRATE_FEATURE` | portes R16 satisfaites | intègre une feature une fois | Git, état, journal | conflit, double intégration |
| `CLOSE_FEATURE` | commit ancêtre et preuves complètes | marque la feature terminée | état et journal | preuve manquante |
| `CONTINUE_PRODUCT` | feature close, produit incomplet | revient à la sélection | état et checkpoint | aucune feature éligible |
| `PAUSE_PRODUCT` | run actif | persiste une pause | état et journal | transition invalide |
| `REBUILD_STATUS` | artefacts lisibles | reconstruit l'état | état dérivé et journal | divergence irrésolue |
| `MARK_BLOCKED` | blocage prouvé | marque le périmètre bloqué | état, incident, journal | preuve insuffisante |
| `MARK_FAILED` | échec terminal prouvé | marque l'échec | état, incident, journal | transition invalide |
| `REQUEST_HUMAN` | cas R15 prouvé | suspend avec dossier de décision | état, incident, diagnostic | dossier incomplet |

Toute autre action est refusée. Chaque exécution vérifie de nouveau ses préconditions et journalise son résultat.

### R13 — Journaux, crash safety et idempotence

Le superviseur tolère un crash entre deux transitions.

Critères d'acceptation :

1. Chaque run produit a un `product_run_id` unique, un namespace stable dérivé de cet identifiant et un journal JSONL append-only horodaté avec timezone explicite.
2. L'intention de transition est persistée avant l'action et son résultat après l'action.
3. La reprise est idempotente : ni double intégration, ni double correction comptée après crash.
4. Les clés d'idempotence identifient run, feature, tâche, action et tentative.
5. Le checkpoint `ProductGraph` est séparé de ceux des features et stocké dans le namespace du run produit.
6. Les identifiants LangGraph du niveau produit et des niveaux feature sont distincts et non réutilisables entre deux runs différents.
7. Les artefacts enfant sont rattachés au run produit tout en préservant la compatibilité des chemins legacy requis par `run-feature` et `run-task`.
8. Un verrou produit et un verrou de feature empêchent les pilotes concurrents.
9. Chaque verrou enregistre au minimum l'identité du run, le PID ou équivalent de propriétaire, un heartbeat et le propriétaire logique.
10. Deux plans utilisant le même `feature_id` ou `task_id` ne peuvent pas écrire simultanément dans les mêmes artefacts, worktrees, checkpoints ou journaux.
11. Les verrous périmés ne sont libérés qu'après vérification du propriétaire, du heartbeat et audit journalisé.

### R14 — Attente, pause et reprise

Critères d'acceptation :

1. Pause et attente sont persistées et distinctes d'un échec.
2. `WAIT_UNTIL` utilise une horloge injectable, une timezone explicite et ne crée aucune boucle d'attente bloquante.
3. Une échéance ou une reprise CLI recharge puis réconcilie toutes les preuves avant action.
4. Une limite fournisseur avec heure de retour devient une attente sans consommer de correction métier.

### R15 — Arrêts humains obligatoires

Critères d'acceptation :

1. Une ambiguïté métier, un conflit Git non résolu, une opération hors scope nécessaire ou le contournement d'une porte d'intégration impose un humain.
2. Une spécification absente sans politique de génération et un incident environnemental persistant au-delà de sa borne imposent un humain.
3. Seul le plafond supervisé absolu de correction, et non le plafond ordinaire, impose un humain.
4. Le dossier transmis contient faits, preuves, décisions à préserver, tentatives et choix possibles.

### R16 — Validations globales et intégration de feature

Critères d'acceptation :

1. Une feature n'est intégrable que si toutes ses tâches sont intégrées, sa couverture vaut 100 %, son rapport est cohérent et ses validations passent.
2. Une baseline produit de référence est exécutée et tracée avant toute tentative de fusion de feature.
3. L'intégration commence par une fusion temporaire sans commit sur la branche produit courante.
4. Les validations de feature sont exécutées sur le résultat fusionné avant tout commit d'intégration.
5. Les validations globales produit sont ensuite exécutées sur le même résultat fusionné.
6. Aucun commit d'intégration n'est créé tant qu'une porte de validation, de scope, de rapport ou de non-régression n'a pas passé.
7. Aucune régression nouvelle n'est acceptée par rapport à la baseline produit de référence.
8. En cas d'échec, un rollback borné, sûr et audité restaure l'état de tentative sans supprimer de preuve ni toucher un état préexistant hors scope.
9. Le commit d'intégration est créé uniquement si toutes les validations sur l'état fusionné passent.
10. Après commit, la présence du commit intégré dans l'historique produit est prouvée par une relation d'ancêtre Git.
11. Une feature dépendante utilise ensuite cette branche produit mise à jour comme base.

### R17 — Clôture produit

Critères d'acceptation :

1. `COMPLETED` exige toutes les features obligatoires terminées, aucune feature requise bloquée et les validations finales passantes.
2. Un rapport final produit est généré et vérifié depuis les preuves structurées.
3. Push, PR, merge distant et release restent désactivés et nécessitent une autorisation distincte.

### R18 — CLI et monitoring

Critères d'acceptation :

1. `autodev run-product PLAN` crée un run et conduit le graphe ; `--resume` peut être un alias documenté de reprise.
2. `autodev product-status PLAN` reconstruit et affiche l'état déterministe.
3. `autodev monitor-product PLAN` observe événements, heartbeat, attente et incidents sans muter le run.
4. `autodev pause-product PLAN` persiste une pause contrôlée.
5. `autodev resume-product PLAN` réconcilie puis reprend idempotemment.
6. Les cinq commandes possèdent des tests CLI de succès, erreurs de contrat et reprise.

### R19 — Incidents réels et non-régression Autodev

Critères d'acceptation :

1. Le caractère `|` dans un argument cité reçoit un traitement sûr et explicite.
2. Les rapports périmés ne contredisent jamais le commit courant.
3. Plusieurs contraintes de correction sont transmises ensemble avec les décisions acquises.
4. Les échecs Vite/Playwright transitoires sont réessayables selon une borne explicite.
5. Les tests unitaires, intégration et E2E couvrent le cycle nominal, FP004-T02, FP004-T03, crash/reprise, divergences Git et collisions entre deux runs concurrents.

## Contraintes techniques

- implémenter en Python dans la couche `autodev/` et réutiliser ses composants avant ceux d'`orchestrator/` ;
- conserver les contrats déterministes existants de revue, scope, tests et intégration ;
- versionner tous les nouveaux schémas JSON ;
- séparer plan, état, checkpoints, journaux et rapports ;
- n'exécuter aucune commande modèle libre et aucune opération destructive globale ;
- tester avec dépendances externes, horloge, runners et Git injectables lorsque pertinent.

## Stratégie d'atomisation attendue

`autodev plan` doit créer des tâches propriétaires distinctes, sans tâche-monstre, couvrant au minimum :

1. plan produit et schéma (`R1`) ;
2. politique de spécification propriétaire (`R20`) ;
3. état séparé et reconstruction (`R2`) ;
4. sélection et dépendances (`R4`) ;
5. taxonomie et schémas d'incidents (`R6`) ;
6. diagnostic Codex structuré et collecteur (`R7`) ;
7. décisions acquises (`R8`) ;
8. moteur de politique et exécuteur d'actions (`R9`, `R12`) ;
9. journaux, namespace, verrous, idempotence et crash safety (`R13`) ;
10. attente, pause et reprise (`R14`) ;
11. Git, dirty state préexistant et réconciliation après interruption (`R11`) ;
12. génération de spécification, validation de spécification et planification (`R5.2` à `R5.4`) ;
13. exécution imbriquée et plafonds de correction (`R3`, `R10`) ;
14. cycle d'intégration transactionnelle et clôture de feature (`R5.5` à `R5.9`, `R16`) ;
15. CLI et monitoring (`R18`) ;
16. clôture produit, E2E Autodev, collisions inter-runs et rapports finaux (`R17`, `R19`).

La matrice de couverture du backlog doit affecter chaque critère numéroté à une et une seule tâche propriétaire et refuser doublon, omission ou couverture inférieure à 100 %.
