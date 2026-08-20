# Guide de packaging Windows NSIS pour Gestion Cimetière

## Vue d'ensemble

Ce guide couvre la préparation et la génération de l'installateur Windows (.exe) pour l'application Gestion Cimetière via NSIS (Nullsoft Scriptable Install System), intégré à Tauri 2.

## Prérequis

### Sur Linux/macOS (développement)

- Node.js 18+ et npm
- Rust + cargo (toolchain stable)
- @tauri-apps/cli 2.x (installé automatiquement via npm)

### Sur Windows (build final)

- Windows 7 SP1 ou supérieur
- Visual Studio Build Tools 2022 ou supérieur (pour support MSVC)
- NSIS 3.x (génération automatique via Tauri)

**Note:** Le build NSIS complet ne peut être effectué que sur Windows. Sur Linux/macOS, le build génère un message d'erreur indiquant que NSIS est introuvable, ce qui est normal.

## Architecture de configuration

### Fichier `src-tauri/tauri.conf.json`

Clés essentielles pour Windows :

```json
{
  "productName": "Gestion Cimetière",
  "version": "0.1.0",
  "identifier": "com.gestion-cimetiere.app",
  "bundle": {
    "active": true,
    "targets": ["nsis"]
  }
}
```

### Icônes

Emplacements et formats requis :

- **Icône application** : `src-tauri/icons/icon.ico`
  - Résolutions recommandées : 16x16, 32x32, 128x128
  - Format : ICO (Windows Icon)
  - Généré automatiquement depuis PNG via `convert` (ImageMagick)

Génération des icônes :

```bash
cd src-tauri/icons
convert 16x16.png 32x32.png 128x128.png icon.ico
```

## Étapes de build

### 1. Préparation de l'environnement

```bash
# Installer les dépendances npm
npm install

# Vérifier la configuration Tauri
npx tauri info
```

### 2. Build du frontend (React + TypeScript)

```bash
npm run build
```

Résultat : Application optimisée générée dans `dist/`

### 3. Build du backend (Rust)

```bash
cargo build --release -p gestion-cimetiere
```

Résultat : Binaire Rust compilé et optimisé

### 4. Build du bundle Windows (NSIS)

**⚠️ Accessible uniquement depuis Windows**

```bash
npm run tauri build
```

Ou spécifiquement pour NSIS :

```bash
npx tauri build -- --target nsis
```

Cela génère :
- `target/release/bundle/nsis/Gestion_Cimetiere_*.exe` — Installateur Windows NSIS

### 5. Alternative : Build sur Linux (prépare, ne compile pas NSIS)

```bash
npm run tauri build
```

Résultat : Erreur à l'étape NSIS (attendue)
Message : `Error: No suitable NSIS toolset found.`

## Configuration Tauri pour NSIS (optionnel)

Pour personnaliser l'installateur NSIS, ajouter une section `bundle.windows` dans `tauri.conf.json` :

```json
{
  "bundle": {
    "active": true,
    "targets": ["nsis"],
    "windows": {
      "certificateThumbprint": null,
      "digestAlgorithm": "sha256",
      "signingIdentity": null,
      "timestampUrl": null
    }
  }
}
```

**Notes :**
- `certificateThumbprint` : Pour signer numériquement (optionnel)
- `timestampUrl` : Serveur d'horodatage (optionnel)

## Métadonnées de l'application

Vérifiées et configurées :

| Clé | Valeur | Description |
| --- | --- | --- |
| `productName` | Gestion Cimetière | Nom affiché à l'installation |
| `version` | 0.1.0 | Version du produit (synchronisée avec package.json) |
| `identifier` | com.gestion-cimetiere.app | Identifiant unique (appli bundle ID) |

## Structure des répertoires de distribution

Après un build complet sur Windows :

```
target/release/bundle/
├── nsis/
│   └── Gestion_Cimetiere_0.1.0_x64.exe    ← Installateur principal
├── msi/                                     ← Alternative MSI (si activée)
└── other/
```

## Processus d'installation (utilisateur final)

1. Télécharger `Gestion_Cimetiere_x.x.x_x64.exe`
2. Exécuter l'installateur
3. Suivre l'assistant d'installation NSIS
4. L'application est installée par défaut dans `C:\Program Files\Gestion Cimetière`
5. Raccourcis créés : Bureau + Menu Démarrage

## Chemins de stockage des données

### Windows

- **Base de données SQLite** : `%APPDATA%\Gestion Cimetière\db.db`
- **Sauvegardes** : `%APPDATA%\Gestion Cimetière\backups/`
- **Logs** : `%APPDATA%\Gestion Cimetière\logs/`

Exemple sur un poste réel :
```
C:\Users\[Mairie]\AppData\Roaming\Gestion Cimetière\
├── db.db
├── backups/
│   └── backup_20260616_143022_123456789.db
└── logs/
```

## Dépannage

### Erreur : "No suitable NSIS toolset found"

**Cause** : Tentative de build sur Linux/macOS (normal)

**Solution** : Build uniquement sur Windows avec les outils MSVC/NSIS installés

### Erreur : "Icon file not found"

**Cause** : `src-tauri/icons/icon.ico` manquant

**Solution** : Générer avec ImageMagick (voir section Icônes)

### Binaire de base de données introuvable

**Cause** : Frontend build incomplet

**Solution** : Exécuter `npm run build` avant `npm run tauri build`

## Prochaines étapes

- **MVP-22** : Configuration AppImage pour Linux
- **MVP-23** : Configuration .deb pour Debian/Ubuntu
- **MVP-26** : Tests E2E incluant l'installation Windows
- **CI/CD** : Intégration du build NSIS dans GitHub Actions (environnement Windows)

## Ressources

- [Documentation Tauri 2.x Bundle](https://tauri.app/docs/guides/distribution/)
- [Documentation NSIS](https://nsis.sourceforge.io/Main_Page)
- [Tauri Windows Target Setup](https://tauri.app/docs/guides/getting-started/prerequisites/)
