# MVP-18 — Implémenter la génération d'un PDF administratif simple pour une concession

**Date :** 2026-06-16  
**Correction QA :** 2026-06-16  
**Agent :** backend  
**Statut :** ✅ Complete (Correction post-QA)

## Objectif

Implémenter la génération d'un **vrai fichier PDF** administratif imprimable pour une concession, contenant au minimum :
- Identité de la concession
- Informations du cimetière
- Informations de l'emplacement
- Données de la concession (statut, dates importantes)
- Titulaire de la concession
- Liste des défunts inhumés
- Date de génération du document

## Fichiers créés / modifiés

**Créés:**
- `src-tauri/src/services/pdf_service.rs` — Service de génération de PDF binaire via printpdf
- `src-tauri/src/commands/pdf.rs` — Commande Tauri `generate_concession_pdf(concession_id)`
- `src-tauri/tests/integration_pdf.rs` — 3 tests d'intégration validant PDF réel

**Modifiés:**
- `src-tauri/src/services/mod.rs` — Export de PdfService
- `src-tauri/src/commands/mod.rs` — Export de la commande pdf
- `src-tauri/src/main.rs` — Enregistrement de la commande dans invoke_handler
- `src-tauri/Cargo.toml` — Ajout dépendance `printpdf = "0.7"`

## Décisions prises

1. **Génération de PDF binaire réel** : Utilisation de `printpdf 0.7`
   - Justification : QA exigeait un vrai PDF (en-tête %PDF, extension .pdf). printpdf est simple, maintenu, et produit des PDFs valides
   - Alternative écartée : genpdf (API complexe en v0.2)

2. **Service de génération découpé** : Architecture par couches (Repository → Service → Commands)
   - Justification : séparation des responsabilités, testabilité, réutilisabilité pour futures améliorations

3. **Chemin de sortie fixe** : Tous les documents générés dans `/tmp/gestion-cimetiere-pdfs`
   - Justification : MVP simple, sans configuration utilisateur ; peut être paramétré après
   - Note: Répertoire créé automatiquement s'il n'existe pas

4. **Nommage des fichiers cohérent** : `Concession_{id}_generated_{timestamp}.pdf`
   - Justification : identifiabilité, chronologie, non collision (timestamp inclus)

5. **Contenu du document** : Format PDF avec sections clairement délimitées
   - Justification : administratif simple, lisible, imprimable, prêt pour usage en mairie

## Problèmes connus et résolution

**Problème initial (QA):** Implémentation précédente généraitun fichier .txt au lieu d'un PDF binaire
- **Résolution :** Intégration de `printpdf 0.7`, rewrite complet du service PDF, tests validant PDF réel

Aucun problème restant. Tous les tests passent, compilation réussie.

## Résultats des tests (après correction)

**Unit tests:**
- `services::pdf_service::tests::test_pdf_filename_format` : ✅ Passing
- `services::pdf_service::tests::test_pdf_header_marker` : ✅ Passing (nouveau, valide en-tête %PDF)
- **Subtotal unit: 2/2 passing** ✅

**Integration tests:**
- `test_integration_pdf_generation_basic` : ✅ Fichier .pdf créé, en-tête %PDF validé
- `test_integration_pdf_with_burials` : ✅ PDF avec inhumation, validation structure
- `test_integration_pdf_with_multiple_burials` : ✅ PDF avec 3 inhumations, contenu complet
- **Subtotal integration: 3/3 passing** ✅

**Full suite:**
- **Total: 60 tests passing, 0 failures** ✅ (vs 54 précédemment)
- No regressions (tous les tests existants restent verts)
- cargo fmt: Clean
- cargo check: Clean
- cargo test --all: Success

## Contraintes respectées

- ✅ Ne pas implémenter les courriers de relance
- ✅ Ne pas implémenter la génération massive
- ✅ Ne pas implémenter les signatures électroniques
- ✅ Pas de modification du frontend
- ✅ Pas de modification de la cartographie
- ✅ Strict MVP : génération simple, pas de dépendances lourdes

## Prochaines étapes

1. **MVP-19** (Frontend) : Intégrer bouton/commande de génération PDF dans les écrans concession
   - Afficher le chemin du fichier généré à l'utilisateur
   - Offrir un lien de téléchargement ou ouverture du fichier

2. **Amélioration PDF** : Convertir le format texte en vrai PDF
   - Option 1 : Utiliser `wkhtmltopdf` externe (nécessite binary système)
   - Option 2 : Utiliser lib Rust `printpdf` ou `genpdf` avec dépendances système minimales

3. **Courriers de relance** : MVP-20+ implémentera courriers d'échéance basés sur alertes (MVP-16)

4. **Export configuré** : Permettre à l'utilisateur de choisir le répertoire de sauvegarde

5. **Signatures électroniques** : Futur, hors MVP (demande legale spécifique)

## Note d'architecture

Le service `PdfService` est découplé de l'infrastructure Tauri et peut être réutilisé :
- Versionning API frontend/backend simple (paramètre: concession_id, résultat: file_path)
- Génération asynchrone possible dans le futur (pas de limit de temps)
- Tests indépendants du système Tauri
