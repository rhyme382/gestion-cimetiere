# Guide de packaging Linux AppImage pour Gestion Cimetière

## Vue d'ensemble

Ce guide couvre la génération et le déploiement de l'application Gestion Cimetière au format AppImage (portable) pour Linux, intégré à Tauri 2.

AppImage offre une distribution simple et portable :
- **Pas de dépendances système** — tout est embarqué dans un seul fichier
- **Pas d'installation** — exécution directe après téléchargement
- **Multi-distribution** — compatible Ubuntu, Debian, Fedora, Arch, etc.
- **Facile pour une mairie** — aucun accès root requis

## Prérequis

### Sur Linux (build et déploiement)

**Pour le build AppImage :**
- Node.js 18+ et npm
- Rust + cargo (toolchain stable)
- @tauri-apps/cli 2.x (installé automatiquement via npm)
- `libssl-dev` (pour certaines dépendances)
- `libxdo-dev` (pour support X11)

**Vérification :**

```bash
# Vérifier les dépendances
node --version   # → v18+ recommandé
npm --version    # → 11+
rustc --version  # → 1.70+
```

### Sur macOS / Windows (n'est pas applicable)

AppImage est spécifique à Linux. Sur macOS/Windows, utiliser les cibles natives (dmg/exe).

## Architecture de configuration

### Fichier `src-tauri/tauri.conf.json`

Configuration pour AppImage :

```json
{
  "productName": "Gestion Cimetière",
  "version": "0.1.0",
  "identifier": "com.gestion-cimetiere",
  "bundle": {
    "active": true,
    "targets": ["nsis", "appimage"]
  }
}
```

**Notes :**
- `targets` inclut maintenant `"appimage"` pour Linux
- `"nsis"` reste pour Windows (multi-cible)
- `identifier` est platform-agnostique

### Icônes

Mêmes ressources que Windows, réutilisables :

- `src-tauri/icons/icon.png` — PNG 128x128 (utilisé par AppImage)
- `src-tauri/icons/128x128.png` — Icône de haute résolution
- `src-tauri/icons/icon.ico` — Windows uniquement (ignoré sur Linux)

**Note :** AppImage préfère les PNG, qui sont déjà disponibles.

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

Résultat : Binaire Rust compilé

### 4. Build du bundle AppImage

**Sur Linux :**

```bash
npm run tauri build
```

Ou spécifiquement pour AppImage uniquement :

```bash
npx tauri build --target appimage
```

Cela génère :
- `target/release/bundle/appimage/Gestion_Cimetiere_x.x.x_x64.AppImage` — Exécutable AppImage portable

**Durée estimée :** 3-5 minutes (selon la machine)

### 5. Vérifier l'artefact généré

```bash
ls -lah target/release/bundle/appimage/
file target/release/bundle/appimage/Gestion_Cimetiere_*.AppImage
```

Exemple de sortie :

```
-rwxr-xr-x  1 user  group  120M  Jun 16 18:45  Gestion_Cimetiere_0.1.0_x64.AppImage
Gestion_Cimetiere_0.1.0_x64.AppImage: ELF 64-bit LSB executable, x86-64, dynamically linked
```

## Test de l'AppImage

### Rendre exécutable

```bash
chmod +x target/release/bundle/appimage/Gestion_Cimetiere_*.AppImage
```

### Exécution

```bash
./target/release/bundle/appimage/Gestion_Cimetiere_*.AppImage
```

L'application se lance directement, sans installation.

## Déploiement utilisateur final

### 1. Télécharger l'AppImage

L'utilisateur télécharge `Gestion_Cimetiere_0.1.0_x64.AppImage` depuis le serveur de distribution.

### 2. Rendre exécutable

```bash
chmod +x Gestion_Cimetiere_0.1.0_x64.AppImage
```

### 3. Exécuter

```bash
./Gestion_Cimetiere_0.1.0_x64.AppImage
```

**Alternative : double-cliquer** depuis le gestionnaire de fichiers (si permission d'exécution définie)

### 4. (Optionnel) Créer un raccourci

Pour intégrer au menu des applications :

```bash
# Copier l'AppImage dans un répertoire standard
mkdir -p ~/.local/opt
cp Gestion_Cimetiere_0.1.0_x64.AppImage ~/.local/opt/

# Créer un fichier .desktop
cat > ~/.local/share/applications/gestion-cimetiere.desktop <<EOF
[Desktop Entry]
Name=Gestion Cimetière
Exec=~/.local/opt/Gestion_Cimetiere_0.1.0_x64.AppImage
Icon=gestion-cimetiere
Type=Application
Categories=Office;
EOF
```

## Chemins de stockage des données

### Linux (AppImage)

- **Base de données SQLite** : `$XDG_DATA_HOME/gestion-cimetiere/db.db`
  - Défaut : `~/.local/share/gestion-cimetiere/db.db`
- **Sauvegardes** : `~/.local/share/gestion-cimetiere/backups/`
- **Logs** : `~/.local/share/gestion-cimetiere/logs/`

**Exemple complet :**

```
~/.local/share/gestion-cimetiere/
├── db.db
├── backups/
│   └── backup_20260616_143022_123456789.db
└── logs/
```

**Avantage :** L'utilisateur peut sauvegarder, restaurer et transférer facilement le répertoire `gestion-cimetiere/`.

## Compatibilité et limitations

### Systèmes Linux supportés

✅ **Testés/Supportés :**
- Ubuntu 18.04+ (LTS et versions récentes)
- Debian 10+ (Buster+)
- Fedora 30+
- Arch Linux
- Linux Mint
- Distributions basées sur Ubuntu/Debian

⚠️ **Anciennes distributions :**
- Glibc < 2.27 peut avoir des problèmes
- Solution : Utiliser une VM avec une distribution plus récente ou fournir `.deb` (MVP-23)

### Architecture CPU

- ✅ x86_64 (64-bit) — supporté (cible par défaut)
- ⏳ ARM64 — nécessite cross-compilation
- ⏳ i386 (32-bit) — déprécié

## Dépannage

### Erreur : "AppImage ne se lance pas"

**Cause :** Permissions d'exécution manquantes

**Solution :**

```bash
chmod +x Gestion_Cimetiere_*.AppImage
```

### Erreur : "error while loading shared libraries"

**Cause :** Dépendance système manquante

**Solution :** Installer les bibliothèques manquantes

```bash
# Sur Ubuntu/Debian
sudo apt install libxdo3 libssl3

# Sur Fedora
sudo dnf install libxdo openssl-libs
```

### Erreur : "failed to build app: Target appimage does not exist"

**Cause :** Mauvaise syntaxe de ligne de commande

**Solution :** Utiliser `npm run tauri build` sans `--target appimage`

```bash
npm run tauri build  # Génère NSIS + AppImage
# OU
npx tauri build --target appimage  # AppImage seulement (syntaxe correcte pour Tauri)
```

### Application se ferme après démarrage

**Cause :** Erreur lors du chargement du frontend ou du backend Rust

**Solution :** Vérifier les logs

```bash
# Exécuter avec sortie de débuggage
RUST_LOG=debug ./Gestion_Cimetiere_*.AppImage
```

## Distribution et mise à jour

### Hébergement

1. **GitHub Releases** (recommandé pour MVP)
   ```bash
   gh release create v0.1.0 target/release/bundle/appimage/Gestion_Cimetiere_*.AppImage
   ```

2. **Serveur web personnalisé**
   - Simple HTTP/HTTPS
   - Lister les versions disponibles

### Mise à jour applicative

Pour MVP, pas d'auto-update intégrée. Utilisateurs :
1. Téléchargent nouvelle version
2. Remplacent ancien AppImage
3. Relancent

**Post-MVP :** Implémenter `tauri-plugin-updater` pour auto-update.

## Prochaines étapes

- **MVP-23** : Configuration `.deb` pour Debian/Ubuntu (distribution via gestionnaire de paquets)
- **MVP-26** : Tests E2E incluant vérification AppImage fonctionnel
- **CI/CD** : Générer AppImage automatiquement sur chaque release (Linux runner GitHub Actions)
- **Post-MVP** : Auto-update, signature des binaires, signatures GPG

## Ressources

- [Documentation Tauri 2.x Bundle — Linux](https://tauri.app/docs/guides/distribution/)
- [Spécification AppImage](https://appimage.org/)
- [AppImage Runtime](https://github.com/AppImage/AppImageKit)
- [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/latest/)
