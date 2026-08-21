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
| `WAIT_PROVIDER_RESET` | incident fournisseur réessayable, provider identifié | persiste `WAITING_PROVIDER_RESET` avec échéance ou backoff | état, incident, journal, horodatage de reprise | date illisible, quota absolu atteint |
| `RECONCILE_WORKTREE` | interruption, divergence ou crash | capture, classe, attribue et réconcilie les modifications | audit Git, inventaire, restauration ciblée | attribution ambiguë, conflit externe |
| `PRESERVE_PARTIAL_CHANGES` | changements utiles détectés, réconciliation terminée | conserve patchs, blobs, diff et inventaire avant toute reprise | inventaire de tentative, patchs, journal | preuve insuffisante, contenu incohérent |
| `REGENERATE_TASK_REPORT` | artefact stale ou contradictoire, preuves courantes lisibles | archive puis régénère les artefacts techniques courants | artefacts run, archives, journal | divergence non expliquée |
| `REQUEST_SCOPE_EXTENSION` | besoin exact hors périmètre démontré | produit un dossier de décision borné | incident, diagnostic, journal | justification insuffisante |
| `APPLY_SCOPE_EXTENSION` | politique autorisante, extension unique et mécanique | met à jour le backlog autorisé de façon traçable | backlog versionné, décision, journal | extension ambiguë, couverture cassée |
| `REQUEST_CRITERION_REALLOCATION` | critère infaisable par le propriétaire courant | produit une réattribution motivée | incident, diagnostic, journal | plusieurs propriétaires possibles |
| `APPLY_CRITERION_REALLOCATION` | politique autorisante, réattribution unique et cohérente | met à jour ownership, dépendances et couverture | backlog versionné, décision, journal | ambiguïté métier, couverture non bijective |
| `RUN_BASELINE_VALIDATION` | commandes validées, contexte de comparaison défini | exécute une baseline déterministe | résultats de validation, signatures, journal | commande invalide, bruit environnemental |
| `REVALIDATE_TASK` | changement significatif, rapport régénéré ou réconciliation faite | relance validations et revue courantes | review-result, validation-results, journal | artefact stale persistant |
| `RESUME_FEATURE` | diagnostic et réconciliation terminés | reprend sans doublon | checkpoints, journal | état incompatible |
| `RETRY_VALIDATION` | incident réessayable, quota disponible | rejoue une validation | résultat de validation | échec persistant |
| `RETRY_REVIEW` | revue réessayable | rejoue la revue | résultat de revue | sortie invalide, quota |
| `REQUEST_CORRECTION` | verdict correction, plafond ordinaire disponible | lance une correction métier | artefacts de correction | scope, plafond atteint |
| `RUN_SUPERVISED_CORRECTION` | critères R10 satisfaits | lance une correction supervisée | correction, décisions, compteurs | plafond absolu, régression |
| `RECOVER_AGENT_GIT_HISTORY` | mutation d'historique attribuable à un agent prouvée | sauvegarde les preuves utiles puis restaure un état autorisé borné | audit Git, snapshots, journal | reflog ambigu, perte potentielle |
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

Critères d'acceptation :

1. Le registre des actions est fermé, versionné et inclut au minimum toutes les actions listées dans le tableau, y compris `WAIT_PROVIDER_RESET`, `RECONCILE_WORKTREE`, `PRESERVE_PARTIAL_CHANGES`, `REGENERATE_TASK_REPORT`, `REQUEST_SCOPE_EXTENSION`, `APPLY_SCOPE_EXTENSION`, `REQUEST_CRITERION_REALLOCATION`, `APPLY_CRITERION_REALLOCATION`, `RECOVER_AGENT_GIT_HISTORY`, `RUN_BASELINE_VALIDATION`, `REVALIDATE_TASK`, `RESUME_FEATURE`, `REQUEST_HUMAN` et `INTEGRATE_FEATURE`.
2. Chaque définition d'action sérialise explicitement ses préconditions, son autorisation de politique, ses entrées structurées, son effet attendu, son périmètre maximal, ses preuves d'audit, sa règle d'idempotence, son rollback éventuel et ses motifs d'arrêt humain.
3. Une action sensible reste refusée par défaut tant qu'aucune politique explicite du plan produit ne l'autorise.
4. Aucune action ne peut autoriser l'écrasement d'une modification utilisateur préexistante, la suppression silencieuse d'un critère, le contournement d'une validation obligatoire, une fusion sans `APPROVED` et `tests PASS` et `scope PASS`, une opération Git destructive non bornée ou une modification fonctionnelle ambiguë sans décision humaine.

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

1. Une ambiguïté métier, un conflit Git non résolu, une opération hors scope nécessaire non couverte par une politique explicite, une réattribution de critère non couverte par une politique explicite ou le contournement d'une porte d'intégration impose un humain.
2. Une extension de scope ou une réattribution de critère ne peut jamais être implicite : en l'absence d'autorisation explicite de politique, l'automate doit produire `REQUEST_HUMAN`.
3. `REQUEST_SCOPE_EXTENSION` et `REQUEST_CRITERION_REALLOCATION` produisent un dossier structuré contenant au minimum besoin exact, fichier ou critère visé, justification, preuve de baseline, impact attendu, alternatives écartées et contraintes à préserver.
4. `APPLY_SCOPE_EXTENSION` et `APPLY_CRITERION_REALLOCATION` ne sont possibles que si la politique du plan les autorise explicitement, si la modification est unique, bornée, mécanique, auditée et sans ambiguïté métier ou fonctionnelle.
5. `REQUEST_HUMAN` reste obligatoire si la politique ne l'autorise pas, si plusieurs solutions raisonnables existent, si l'impact fonctionnel est ambigu ou si la sûreté Git ne peut pas être garantie.
6. Une spécification absente sans politique de génération et un incident environnemental persistant au-delà de sa borne imposent un humain.
7. Seul le plafond supervisé absolu de correction, et non le plafond ordinaire, impose un humain.
8. Le dossier transmis contient faits, preuves, décisions à préserver, tentatives et choix possibles.

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

### R21 — Incidents fournisseur, quotas et attente bornée

Critères d'acceptation :

1. Le superviseur distingue explicitement les incidents `Claude`, `Codex` et tout autre fournisseur déclaré, sans fusionner leurs compteurs, messages ou politiques de reprise.
2. Les messages de limite de session, quota, rate limit, indisponibilité temporaire et erreur fournisseur sont reconnus par taxonomie fermée, avec conservation du message brut et d'une classification normalisée.
3. Le message exact `You've hit your session limit · resets 7:10pm (Europe/Paris)` est parsé comme incident fournisseur réessayable avec timezone `Europe/Paris`.
4. Lorsqu'une heure ou date de renouvellement est présente, le superviseur dérive un `retry_at` horodaté, fiable, sérialisé avec timezone explicite et recalculable de manière déterministe.
5. Lorsqu'aucune date fiable n'est disponible, la politique applique un backoff borné, auditable et plafonné sans consommer de correction métier.
6. L'état `WAITING_PROVIDER_RESET` est persisté, observable par monitoring, reprenable automatiquement à échéance et distinct de `FAILED`, `BLOCKED` et `PAUSED`.
7. Un incident fournisseur temporaire ne déclenche ni correction métier, ni restauration destructive, ni perte du worktree, de l'index, du commit courant ou des fichiers modifiés.
8. Les journaux d'incident enregistrent au minimum le fournisseur, le type d'erreur, le message brut, la timezone source, l'échéance retenue, la politique appliquée et la décision de reprise ou d'escalade.
9. `REQUEST_HUMAN` n'est autorisé pour un incident fournisseur que si la politique ne permet plus d'attendre, si le quota absolu est atteint ou si l'échéance reste indéterminable de façon sûre.
10. Des tests unitaires et d'intégration reproduisent le message exact observé, la persistance `WAITING_PROVIDER_RESET`, la reprise automatique après l'heure de renouvellement et le cas sans date fiable.

### R22 — Réconciliation fine du worktree et empreintes de contenu

Critères d'acceptation :

1. Chaque tentative capture un état Git avant lancement agent, après hooks de démarrage et après processus, y compris `HEAD`, branche, index, tracked dirty, untracked et métadonnées de worktree.
2. La réconciliation distingue modifications préexistantes, modifications de hook, modifications agent et modifications externes postérieures au lancement.
3. La détection compare le contenu et non la seule présence des chemins, via des empreintes déterministes par fichier couvrant blob indexé, contenu worktree et fichiers non suivis.
4. Une nouvelle modification sur un fichier déjà sale est détectée même si le chemin est identique avant et après tentative.
5. Le verdict `no_allowed_changes` est interdit dès qu'une empreinte change sur un chemin autorisé ou sur un fichier non suivi autorisé.
6. Le superviseur conserve un inventaire des patchs, blobs ou diffs produits par tentative avant toute restauration ou reprise.
7. Les modifications autorisées cohérentes peuvent être reprises cumulativement ; toute ambiguïté d'attribution, divergence externe ou incohérence de contenu impose `REQUEST_HUMAN`.
8. Aucune restauration ne peut écraser une modification préexistante ou de hook prouvée comme indépendante de la tentative courante.
9. Toute réconciliation produit des preuves vérifiables reliant les captures avant/après, les empreintes, les classements et la décision prise.
10. Les validations et la revue sont relancées après tout changement significatif détecté par empreinte ou réconciliation.
11. Des tests reproduisent au minimum un worktree partiel après interruption, le cas FP004-T03 où les mêmes chemins restent présents mais avec contenu différent, et une reprise idempotente après crash.

### R23 — Mutations Git agent interdites et récupération bornée

Critères d'acceptation :

1. Un agent d'implémentation ne peut exécuter ni `commit`, ni `commit --amend`, ni `reset`, ni `rebase`, ni `cherry-pick`, ni `merge`, ni `branch -f`, ni `update-ref`, ni aucune mutation d'historique équivalente.
2. La restriction doit être effective soit par réduction de capacités du runner, soit par contrôle post-exécution capable de détecter une divergence de `HEAD`, branche, références et reflog.
3. Le superviseur capture avant et après tentative `HEAD`, branche active, références pertinentes et reflog borné afin de détecter toute chaîne `commit -> amend -> reset -> nouveau commit`.
4. Lorsqu'une mutation d'historique attribuable à l'agent est détectée, les commits et contenus utiles sont sauvegardés avant toute récupération.
5. La récupération d'historique est bornée par politique, auditée et interdite si elle risque d'écraser une modification utilisateur préexistante ou si l'ambiguïté du reflog empêche une restauration sûre.
6. La séparation des rôles est stricte : Claude agent d'implémentation modifie uniquement les fichiers autorisés et n'exécute aucun `commit`, `commit --amend`, `reset`, `rebase`, `merge`, `cherry-pick` ni mutation de référence Git ; Codex reviewer produit un verdict structuré sur le commit et les preuves courantes ; Codex superviseur produit un diagnostic structuré et propose des actions typées ; seul l'orchestrateur Python applique la politique, exécute les actions autorisées, gère Git, commits, checkpoints, intégrations, pauses et reprises.
7. Les opérations Git destructives non autorisées restent interdites même en présence d'un incident concurrent.
8. Les journaux conservent la chaîne exacte de commits, références et reflog utilisée pour détecter puis récupérer l'incident.
9. Un test d'intégration reproduit `commit_initial -> amend_agent -> reset_agent -> nouveau_commit` et prouve la détection, la sauvegarde des contenus utiles et la récupération bornée.

### R24 — Fraîcheur des artefacts techniques et rapports narratifs

Critères d'acceptation :

1. Le commit courant, le diff courant, les validations relancées et les empreintes de leurs artefacts sont les preuves autoritatives ; un rapport narratif n'a jamais autorité contre elles.
2. Le superviseur détecte les artefacts stale via `commit`, `base_commit`, empreinte de diff, empreinte de validations et identité du worktree courant.
3. Il distingue au minimum rapport narratif, `task-report.json`, `review-result.json`, `current-paths.json` et `validation-results.json`.
4. Tout artefact périmé est archivé avec son contexte de tentative avant régénération déterministe des artefacts techniques courants.
5. Une ancienne revue ne peut plus affirmer `TESTS FAIL` si les validations courantes régénérées sont `PASS`, sauf divergence explicitement expliquée et tracée.
6. L'opération de régénération est idempotente et ne détruit jamais la traçabilité des tentatives antérieures.
7. Une divergence réelle entre preuves courantes non expliquée bloque l'automatisation et impose `REQUEST_HUMAN`.
8. Si un rapport narratif devient factuellement faux, un rapport narratif factuel est régénéré à partir des preuves techniques sans inventer de modifications inexistantes.
9. Des tests reproduisent `task-report.json` stale après changement de commit, `review-result FAIL` contre validations actuelles `PASS` et un récit ancien contredisant les fichiers réellement modifiés.

### R25 — Faisabilité des critères et réattribution contrôlée

Critères d'acceptation :

1. Avant exécution d'une tâche, le superviseur audite la faisabilité de chaque critère owned selon propriétaire, dépendances, `allowed_paths`, composants nécessaires et validations requises.
2. Les contradictions entre `acceptance_criteria`, ownership courant, dépendances et `allowed_paths` sont détectées avant lancement d'agent.
3. Lorsqu'un critère ne peut être implémenté dans le périmètre autorisé, le superviseur identifie la tâche réellement capable de le porter et produit une proposition structurée de réattribution motivée.
4. La propriété d'un critère ne peut jamais être modifiée silencieusement.
5. `REQUEST_CRITERION_REALLOCATION` ne modifie rien implicitement et produit une proposition structurée identifiant le critère visé, le propriétaire courant, le propriétaire proposé, les preuves de non-faisabilité, les dépendances touchées et les validations à recalculer.
6. Une réattribution automatique n'est permise que si le plan produit l'autorise explicitement et si le changement est borné, cohérent, unique, auditable, sans ambiguïté métier et attribuable à une seule tâche capable de l'implémenter.
7. Toute réattribution appliquée recalcule couverture, dépendances, validations requises et propriétaire unique du critère sans altérer les critères déjà intégrés.
8. Si la politique ne l'autorise pas, si plusieurs tâches peuvent raisonnablement porter le critère, si la décision implique une ambiguïté métier ou si la sûreté Git et la bijection de couverture ne peuvent être garanties, `REQUEST_HUMAN` est imposé.
9. Un test reproduit le cas d'un critère initialement attribué à une tâche incapable de modifier les composants nécessaires et vérifie la proposition de réattribution vers la tâche effectivement capable.

### R26 — Extensions minimales de périmètre et baseline différentielle

Critères d'acceptation :

1. Toute demande d'extension compare l'erreur observée sur la branche baseline de tâche et sur la branche de tentative afin de distinguer défaut préexistant, régression introduite, besoin de compatibilité ou demande hors périmètre.
2. `REQUEST_SCOPE_EXTENSION` ne modifie jamais le backlog implicitement et produit une proposition structurée identifiant le fichier exact visé, la preuve bloquante, la baseline de comparaison, la justification mécanique et les contraintes à préserver.
3. L'extension proposée est exacte au fichier près ; l'ouverture large d'un dossier ou d'un module est interdite.
4. Chaque extension est justifiée par un critère explicite ou par une validation obligatoire bloquante.
5. La version précédente du backlog ou de la décision de scope est sauvegardée avant toute application.
6. L'audit consigne qui a décidé, sur quelle preuve, pour quel fichier et sous quelle autorisation de politique.
7. `APPLY_SCOPE_EXTENSION` n'est permise que si la politique l'autorise explicitement et s'il s'agit d'une correction mécanique bornée sans ambiguïté fonctionnelle ou métier.
8. Ownership, dépendances et hors-périmètre métier doivent rester inchangés par défaut lors d'une extension mécanique.
9. Une validation obligatoire ne peut jamais être masquée, supprimée ni contournée pour éviter une extension de scope.
10. Si la politique ne l'autorise pas, si plusieurs extensions raisonnables existent, si l'impact fonctionnel est ambigu ou si la sûreté Git ne peut être garantie, `REQUEST_HUMAN` est imposé.
11. Les tests reproduisent au minimum les besoins exacts sur `plot_repo.rs`, `dto/plot.rs` et l'erreur baseline `aria-invalid` de `ParametresPage.tsx`.

### R27 — Validation sûre des commandes et ressources transitoires locales

Critères d'acceptation :

1. La validation des commandes analyse lexicalement les arguments et distingue métacaractères shell actifs de caractères littéraux contenus dans un argument.
2. Les validations sont exécutées sans shell ; redirections, substitutions, chaînages effectifs et pseudo-commandes mal formées sont refusés.
3. Un motif regex légitime contenant `|` dans un argument transmis à `rg` est accepté lorsqu'il reste un argument littéral.
4. Les préfixes d'environnement légitimes sont acceptés lorsqu'ils sont passés via `env` ou une structure équivalente, tandis qu'une pseudo-commande dont `argv[0]` vaut `PYTHONPATH=...` est rejetée ; une validation exécutable doit être sérialisée sous forme d'argv direct, par exemple `env PYTHONPATH=autodev/src pytest -q ...`, et jamais comme `PYTHONPATH=autodev/src pytest -q ...` sans shell.
5. Les commandes de validation générées sont testées et validées automatiquement sur l'ensemble du backlog avant tout lancement effectif, puis échouent tôt avec diagnostic structuré si elles ne sont pas sûres ou pas directement exécutables sans shell.
6. Les validations transitoires identifient les ports, processus liés au worktree et ressources locales pertinentes sans jamais arrêter un processus étranger ou non identifié.
7. Un conflit de port ou un processus résiduel identifié comme local au worktree peut déclencher un retry limité, journalisé et comparable à la baseline ; sinon `REQUEST_HUMAN` est imposé.
8. Les tests reproduisent au minimum un `rg` avec pipe littéral, `env PYTHONPATH=autodev/src pytest`, une pseudo-commande rejetée avec `PYTHONPATH=...` en `argv[0]`, et un retry Vite/Playwright avec conflit de port identifié.

### R28 — Registre des acquis et corrections cumulatives sans régression

Critères d'acceptation :

1. Le superviseur maintient un registre des acquis validés par critère, décision et signature de validation afin de préserver les points déjà passés.
2. Toute correction reçoit simultanément l'ensemble des critères encore ouverts et des acquis déjà validés comme contraintes à préserver.
3. Après chaque correction, le superviseur vérifie explicitement qu'aucun critère précédemment `PASS` ne repasse `FAIL` sans justification structurée.
4. Les quotas fournisseur, incidents techniques, artefacts stale et attentes fournisseur ne consomment pas le budget de corrections métier.
5. Le dépassement du plafond ordinaire déclenche un diagnostic structuré préalable à toute correction supervisée supplémentaire.
6. Un budget absolu borné est imposé au niveau superviseur ; son dépassement seul peut mener à `REQUEST_HUMAN`.
7. Si deux exigences ou acquis deviennent contradictoires, le superviseur escalade au lieu de choisir implicitement l'une contre l'autre.
8. Un test d'intégration reproduit une correction cumulative de type FP004-T02 où plusieurs tentatives successives préservent tous les acquis déjà validés jusqu'au verdict final.

### R29 — Persistance durable du plan produit et autonomie multi-feature

Critères d'acceptation :

1. Le système distingue plan produit versionné, backlog feature généré et décisions runtime éphémères ou reconstructibles.
2. Toute décision approuvée nécessaire à la reproductibilité, notamment réattribution de critère ou extension de scope, est persistée dans un emplacement durable versionnable ou exportable sans exiger la version de tous les artefacts éphémères.
3. Une régénération de backlog conserve ou reconstruit de manière déterministe les décisions durables déjà approuvées, avec détection des conflits éventuels.
4. Le `ProductGraph` lit un plan produit global, identifie les features déjà intégrées, respecte les dépendances, sélectionne la prochaine feature de manière déterministe puis enchaîne jusqu'à clôture complète du produit ou décision humaine indispensable.
5. La branche produit courante reste la seule base exécutoire ; chaque feature est préparée, planifiée, exécutée, supervisée, validée puis intégrée transactionnellement avant la suivante.
6. Le superviseur gère quota, pause, reprise, crash, hooks et incidents sur plusieurs features successives sans perdre l'état reconstruit ni réintégrer deux fois la même feature.
7. Des tests d'intégration reproduisent au minimum deux features successives avec dépendance satisfaite, un crash puis une reprise idempotente, et un arrêt humain lorsqu'une ambiguïté produit ou périmètre demeure.

## Contraintes techniques

- implémenter en Python dans la couche `autodev/` et réutiliser ses composants avant ceux d'`orchestrator/` ;
- conserver les contrats déterministes existants de revue, scope, tests et intégration ;
- versionner tous les nouveaux schémas JSON ;
- séparer plan, état, checkpoints, journaux et rapports ;
- n'exécuter aucune commande modèle libre et aucune opération destructive globale ;
- tester avec dépendances externes, horloge, runners et Git injectables lorsque pertinent.

## Stratégie d'atomisation attendue

`autodev plan` doit créer des tâches propriétaires distinctes, sans tâche-monstre, de taille atomique mais réellement exécutable. Chaque critère `R1` à `R29` doit avoir exactement une tâche propriétaire responsable de son implémentation, même si une tâche couvre plusieurs exigences cohérentes. Une tâche doit pouvoir modifier les fichiers réellement nécessaires à son exigence, pas un périmètre arbitrairement large ni un chemin impossible à atteindre.

Atomisation minimale attendue :

1. schéma du plan produit et validation structurelle (`R1`) ;
   propriétaire typique : module produit de schéma/chargement ;
   fichiers réalistes : modules `product_plan*`, schémas JSON et leurs tests.
2. politique de spécification propriétaire (`R20`) ;
   propriétaire typique : pipeline de spécification produit ;
   fichiers réalistes : modules de politique de spécification, validation structurée, tests dédiés.
3. état produit séparé, reconstruction et persistance durable (`R2`, `R29.1` à `R29.3`) ;
   propriétaire typique : modules d'état produit, reconstruction et sérialisation ;
   fichiers réalistes : `product_state*`, `feature_status*`, stockage runtime, tests d'état.
4. architecture `ProductGraph -> FeatureGraph -> TaskGraph` et exécution produit nominale (`R3`, `R5`, `R29.4`, `R29.5`) ;
   propriétaire typique : `run_product.py` ou module équivalent ;
   fichiers réalistes : graphe produit, adaptateurs `run_feature`, tests d'intégration.
5. sélection de feature, dépendances Git et préparation de base produit (`R4`) ;
   propriétaire typique : logique de sélection produit et contexte Git ;
   fichiers réalistes : modules `product_selection*`, `git_context*`, tests Git ciblés.
6. taxonomie fermée des incidents (`R6`) ;
   propriétaire typique : schéma/registre d'incidents ;
   fichiers réalistes : schémas JSON, enums Python, tests de validation.
7. diagnostic Codex superviseur et collecteur de preuves courantes (`R7`) ;
   propriétaire typique : `review_task.py`/collecteur produit distinct ;
   fichiers réalistes : modules `product_diagnostic*`, `task_report.py`, tests de schéma.
8. registre des décisions acquises et décisions durables (`R8`, `R28.1`, `R29.2`) ;
   propriétaire typique : registre des décisions/acquis ;
   fichiers réalistes : modules `decision_registry*`, `task_report.py`, tests de persistance.
9. politique déterministe et liste fermée des actions (`R9`, `R12`) ;
   propriétaire typique : moteur de politique produit ;
   fichiers réalistes : modules `product_policy*`, `product_actions*`, tests de refus/autorisations.
10. runtime produit, namespaces, idempotence, verrous et crash safety (`R13`) ;
    propriétaire typique : couche runtime/checkpoint produit ;
    fichiers réalistes : `run_product.py`, stockage de run, verrous, tests de crash/reprise.
11. quotas fournisseur, taxonomie de reprise et `retry_at` (`R21`) ;
    propriétaire typique : runners Claude/Codex et politique fournisseur ;
    fichiers réalistes : runners, parseurs d'incident fournisseur, tests de quota.
12. attente, pause et reprise temporisée (`R14`) ;
    propriétaire typique : orchestration produit et CLI de reprise ;
    fichiers réalistes : `run_product.py`, `monitor_product.py`, `pause_product.py`, tests CLI.
13. snapshots Git complets avant/après tentative (`R11.1`, `R11.8`, `R11.13`, `R22.1`) ;
    propriétaire typique : `git_tools` / `git_context` ;
    fichiers réalistes : helpers de snapshots Git et tests d'attribution.
14. empreintes de contenu, modifications répétées et réconciliation des fichiers déjà modifiés (`R11`, `R22`) ;
    propriétaire typique : logique de réconciliation ;
    fichiers réalistes : `correct_task.py`, `git_context.py`, `task_report.py`, tests de réconciliation.
15. attribution des mutations de hooks (`R11.2`, `R11.13`, `R22.2`) ;
    propriétaire typique : audit de tentative Git ;
    fichiers réalistes : `git_context.py`, `git_tools.py`, tests sur `AGENTS.md`.
16. protection contre les mutations Git agent et récupération d'historique bornée (`R23`) ;
    propriétaire typique : runners Claude, audit Git et récupération ;
    fichiers réalistes : runners, `git_tools.py`, `correct_task.py`, tests reflog/intégration.
17. fraîcheur des artefacts, régénération et revalidation (`R24`) ;
    propriétaire typique : revue et rapports techniques ;
    fichiers réalistes : `review_task.py`, `task_report.py`, tests d'artefacts stale.
18. audit de faisabilité des critères (`R25.1` à `R25.4`) ;
    propriétaire typique : planification/backlog ;
    fichiers réalistes : planificateur, validations backlog, tests de faisabilité.
19. réattribution contrôlée des critères (`R25.5` à `R25.9`) ;
    propriétaire typique : politique produit et backlog versionné ;
    fichiers réalistes : modules de politique, backlog, tests de réattribution.
20. baseline différentielle et extension minimale de scope (`R26`) ;
    propriétaire typique : baseline de validation et politique de scope ;
    fichiers réalistes : `correct_task.py`, `validation_baseline.py`, backlog, tests d'extension.
21. validation sécurisée et exécutable des commandes (`R27.1` à `R27.5`) ;
    propriétaire typique : `task_runner.py` et validation de commandes ;
    fichiers réalistes : `task_runner.py`, tests de commandes sûres/exécutables.
22. incidents Vite/Playwright, ports et ressources locales transitoires (`R19.4`, `R27.6` à `R27.8`) ;
    propriétaire typique : validation runtime locale ;
    fichiers réalistes : `validation_baseline.py`, `integrate_task.py`, tests Playwright/Vite.
23. préparation de feature et couverture propriétaire (`R5.1` à `R5.4`) ;
    propriétaire typique : planification de feature ;
    fichiers réalistes : `run_feature.py`, modules planner, tests de couverture.
24. exécution ProductGraph / FeatureGraph et plafonds de correction (`R10`, `R28.4` à `R28.8`) ;
    propriétaire typique : `run_feature.py` et superviseur produit ;
    fichiers réalistes : `run_feature.py`, modules superviseur, tests FP004-T02.
25. intégration transactionnelle de feature et baseline produit (`R16`) ;
    propriétaire typique : intégration produit/feature ;
    fichiers réalistes : `integrate_task.py`, `run_product.py`, `validation_baseline.py`, tests d'intégration.
26. clôture produit et rapport final (`R17`) ;
    propriétaire typique : clôture produit ;
    fichiers réalistes : `run_product.py`, `task_report.py` ou rapport produit dédié, tests finaux.
27. CLI produit et monitoring non mutateur (`R18`) ;
    propriétaire typique : `cli.py`, lecture d'état et monitor ;
    fichiers réalistes : CLI, `monitor_state.py`, tests CLI/monitoring.
28. tests multi-feature, collisions concurrentes et non-régression Autodev (`R19`, `R29.6`, `R29.7`) ;
    propriétaire typique : suite d'intégration/E2E produit ;
    fichiers réalistes : tests d'intégration produit, fixtures Git, rapports correspondants.

Dépendances minimales de planification :

1. plan produit et politique de spécification avant toute sélection ou exécution ;
2. plan et état reconstruit avant sélection ;
3. taxonomie d'incidents avant diagnostic ;
4. snapshots Git avant empreintes, attribution et réconciliation ;
5. empreintes avant réconciliation des fichiers déjà modifiés ;
6. registre des décisions acquises avant corrections cumulatives ;
7. politique et liste fermée des actions avant toute action sensible ;
8. quotas fournisseur avant attente ou reprise temporisée ;
9. snapshots Git avant récupération d'historique ;
10. faisabilité des critères avant préparation et exécution d'une feature ;
11. baseline différentielle avant extension de scope ;
12. artefacts frais avant revue ou rediagnostic ;
13. exécution feature avant intégration ;
14. intégration avant clôture ;
15. CLI et monitoring après disponibilité des composants qu'ils exposent.

Règles de scope des futures tâches :

1. chaque tâche doit pouvoir modifier les fichiers strictement nécessaires à son exigence ;
2. la réconciliation peut viser `correct-task` et ses tests, pas un dossier produit entier ;
3. la validation sécurisée des commandes peut viser `task_runner.py` et ses tests ;
4. la gestion des artefacts stale peut viser `review_task.py`, `task_report.py` et leurs tests ;
5. la gestion des quotas et de l'interdiction Git peut viser les runners Claude/Codex et les tests associés ;
6. la reprise temporisée et les plafonds peuvent viser `run_feature.py` ou le module produit équivalent et ses tests ;
7. les snapshots complets peuvent viser `git_tools.py`, `git_context.py` et les tests Git exacts ;
8. la CLI produit peut viser `cli.py`, les commandes produit dédiées et leurs tests ;
9. chaque tâche doit inclure les rapports et tests correspondants sans ouvrir de chemins non nécessaires.

Règles de concurrence minimales :

1. aucun workflow concurrent ne peut exécuter la même feature ;
2. un verrou produit et un verrou feature sont obligatoires ;
3. la politique de concurrence fournisseur est distincte de la concurrence Git et peut sérialiser Claude si un compte ou un quota est partagé ;
4. `monitor-product` est strictement non mutateur ;
5. aucune double reprise, aucune double intégration et aucune double clôture ne sont autorisées.

La matrice de couverture du backlog doit affecter chaque critère numéroté à une et une seule tâche propriétaire et refuser doublon, omission ou couverture inférieure à 100 %.
