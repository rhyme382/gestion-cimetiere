# Rapport MVP-08 : Stratégie packaging et pipeline de build

**Date** : 2026-06-15  
**Agent responsable** : packaging  
**Statut** : Initié  

## Objectif

Définir et implémenter la stratégie packaging multi-plateforme (NSIS/Windows, AppImage/Linux, .deb/Linux) avec pipeline de build reproductible, sans développement métier.

## Dépendances

- MVP-01 stabilisé
- MVP-02 terminé

## Architecture cible

### Windows

**Technologie** : NSIS (Nullsoft Scriptable Install System)

- Installateur MSI auto-exécutable
- Gestion des associations fichiers
- Raccourcis Bureau/Menu Démarrage
- Désinstallation propre

### Linux

**Plateforme principale** : AppImage

- Portable et sans dépendances système
- Exécution immédiate après téléchargement
- IdéAL pour une mairie sans accès root

**Alternative** : `.deb` (Debian/Ubuntu)

- Distribution via gestionnaire de paquets
- Dépendances système gérées
- Mises à jour automatisées

## Configuration Tauri

Fichiers à configurer :

- `tauri.conf.json` : Paramètres NSIS, AppImage, `.deb`
- Icônes et ressources (format `.ico`, `.png`)
- Métadonnées (version, productName, copyright)

## Fichiers modifiés

- `orchestration/prompts/packaging_agent.md` (ajout section MVP-08)
- `reports/dev/MVP-08.md` (ce rapport)
- `agents/STATUS.md` (mise à jour statut)

## Décisions

1. Utiliser Tauri pour la gestion centralisée du packaging
2. Prioriser la simplicité pour les mairies (AppImage d'abord)
3. Documenter chaque format de packaging
4. Créer des scripts de test des artefacts

## Problèmes connus

Aucun à ce stade.

## Résultats des tests

En attente de mise en place de la configuration.

## Étapes suivantes

1. Stabiliser la configuration Tauri `tauri.conf.json`
2. Implémenter les scripts NSIS
3. Configurer les builds AppImage
4. Tester les installateurs sur machines réelles
5. Créer le guide utilisateur d'installation
6. Intégrer au CI/CD

## Notes de suivi

- Vérifier la reproductibilité des builds à chaque modification
- Tester les chemins d'installation locaux (Documents, Program Files, etc.)
- Valider la désinstallation propre
