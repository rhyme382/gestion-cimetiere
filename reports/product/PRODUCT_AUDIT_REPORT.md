# PRODUCT_AUDIT_REPORT

## objectif

Construire un backlog produit exhaustif du logiciel municipal cible, distinct du backlog `alpha-recovery`, en s'appuyant sur `SPEC.md`, `ROADMAP.md`, le depot reel, le schema SQLite, les tests, le packaging et les rapports.

## methode

- lecture croisee des specifications, roadmap, audit alpha existant, backlog archive, frontend, backend, migrations, tests et rapports ;
- verification de la capacite réellement offerte dans l application packagee plutot que confiance aveugle dans les anciens verdicts ;
- extension du perimetre vers le produit final, domaine par domaine, avec taches atomiques, phases et dependances orientees backend avant UI.

## synthese

Le premier audit reste valide pour la remise en etat Alpha-0. Ce second audit montre cependant qu un logiciel municipal comparable aux meilleurs outils etudies exige une cible bien plus large : 30 domaines, 90 taches atomiques, un modele de donnees fortement enrichi et des preuves packagées bien plus exigeantes.

Constats determinant le backlog :
- le backend actuel constitue un socle exploitable mais restreint ;
- le frontend actuel reste majoritairement lecture seule ;
- la cartographie de consultation n est pas encore reliée au réel ;
- la suite backend Rust est reproductible ; la suite frontend échoue actuellement faute de `@testing-library/dom` ;
- les preuves de packaging, d E2E réel et d exploitation réglementaire complète restent insuffisantes pour la cible finale.

## livrables produits

- `product/FEATURE_MATRIX.md` : catalogue cible par domaine, mis en regard de l etat observe ;
- `product/GAP_ANALYSIS.md` : analyse d ecarts exhaustive avec modele domaine cible ;
- `product/USER_JOURNEYS.md` : parcours utilisateur finaux structurants ;
- `product/ALPHA_ROADMAP.md` : roadmap produit et chemin critique ;
- `tasks/backlog.json` : backlog exhaustif atomique conforme au schema demande ;
- `reports/product/PRODUCT_AUDIT_REPORT.md` : synthese et metriques du second audit.

## metriques

- nombre de domaines : 30
- nombre de taches : 90
- nombre de taches ALPHA-0 : 12
- nombre de taches ALPHA-1 : 25
- nombre de taches ALPHA-2 : 24
- nombre de taches BETA-1 : 12
- nombre de taches BETA-2 : 14
- nombre de taches POST-BETA : 3
- nombre de taches critiques : 28
- dependances racines : FP-001, FP-013, FP-070, FP-076
- premier chemin critique recommande : `FP-001 -> FP-004 -> FP-005 -> FP-010 -> FP-011 -> FP-013 -> FP-014 -> FP-019 -> FP-020 -> FP-022 -> FP-023 -> FP-037 -> FP-038 -> parcours UI fondamentaux`

## verifications executees pendant cet audit

- `cargo test --manifest-path src-tauri/Cargo.toml -- --list` : 91 tests backend repertories ;
- `npm test -- --run` : echec reproductible cote frontend, module `@testing-library/dom` manquant ;
- lecture des specs Playwright : couverture majoritairement presence/visibilite, peu de preuves de parcours metier complets ;
- lecture des rapports release : artefacts, workflow et validation finale se contredisent encore sur plusieurs points.

## conclusion

La cible produit finale ne peut pas etre ramenée aux 15 taches de remise en etat alpha. Le logiciel complet demande un backlog nettement plus large, couvrant non seulement le noyau concession/defunt/cartographie, mais aussi les espaces cinéraires, les procédures, la documentation, la sécurité locale, l audit, l import, le RGPD, le packaging prouvé et l aide utilisateur.