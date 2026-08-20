# Guide de packaging Linux .deb pour Gestion Cimetière

## Vue d'ensemble

Ce guide couvre la génération et le déploiement de l'application Gestion Cimetière au format `.deb` (Debian Package) pour les distributions Debian et Ubuntu, intégré à Tauri 2.

Le format `.deb` offre une distribution professionnelle et maintenue :
- **Installation via gestionnaire de paquets** — `apt install` comme une application système
- **Dépendances gérées automatiquement** — Système vérifie les prérequis avant install
- **Mises à jour centralisées** — Peut être mis à jour via `apt upgrade`
- **Intégration système complète** — Menu applications, racourcis, variables d'environnement
- **Distribution officielle** — Compatible avec les dépôts Debian/Ubuntu standards

## Prérequis

### Sur Linux (build et déploiement)

**Pour le build .deb :**
- Node.js 18+ et npm
- Rust + cargo (toolchain stable)
- @tauri-apps/cli 2.x (installé automatiquement via npm)
- `dpkg` — Outils Debian de packaging (installé par défaut)
- `dpkg-dev` — Outils de développement Debian
- `build-essential` — Compilateurs et outils de build

**Installation des dépendances :**

```bash
# Sur Debian/Ubuntu
sudo apt update
sudo apt install -y dpkg dpkg-dev build-essential
```

**Vérification :**

```bash
dpkg --version
node --version   # → v18+ recommandé
rustc --version  # → 1.70+
```

### Sur macOS / Windows (n'est pas applicable)

.deb est spécifique à Debian/Ubuntu. Sur macOS/Windows, utiliser les cibles natives (dmg/exe).

## Architecture de configuration

### Fichier `src-tauri/tauri.conf.json`

Configuration pour .deb :

```json
{
  "productName": "Gestion Cimetière",
  "version": "0.1.0",
  "identifier": "com.gestion-cimetiere",
  "bundle": {
    "active": true,
    "targets": ["nsis", "appimage", "deb"]
  }
}
```

**Notes :**
- `targets` inclut maintenant `"deb"` pour Debian/Ubuntu
- `"nsis"` reste pour Windows
- `"appimage"` reste pour Linux portable
- `identifier` est identique pour toutes les cibles

### Métadonnées Debian

Tauri génère automatiquement les fichiers de contrôle Debian à partir de la configuration :

- **Package name** : dérivé de `productName` (généré : `gestion-cimetiere`)
- **Version** : de `bundle.version` (défaut : `0.1.0`)
- **Maintainer** : À configurer (voir section dédiée)
- **Description** : À configurer
- **Architecture** : auto-détectée (amd64, arm64, etc.)
- **Dépendances** : gérées par Tauri (libc, webkit2gtk, etc.)

### Icônes

Mêmes ressources que les autres cibles :

- `src-tauri/icons/icon.png` — PNG 128x128 (utilisé par .deb)
- `src-tauri/icons/128x128.png` — Icône haute résolution

## Étapes de build

### 1. Préparation de l'environnement

```bash
# Installer les dépendances npm
npm install

# Installer les dépendances système (si non présentes)
sudo apt install -y dpkg dpkg-dev

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

### 4. Build du bundle .deb

**Sur Debian/Ubuntu :**

```bash
npm run tauri build
```

Ou spécifiquement pour .deb uniquement :

```bash
npx tauri build --target deb
```

Cela génère :
- `target/release/bundle/deb/gestion-cimetiere_0.1.0_amd64.deb` — Package Debian

**Durée estimée :** 3-5 minutes (identique à AppImage)

### 5. Vérifier l'artefact généré

```bash
ls -lah target/release/bundle/deb/
file target/release/bundle/deb/gestion-cimetiere_*.deb
dpkg -I target/release/bundle/deb/gestion-cimetiere_*.deb
```

Exemple de sortie :

```
-rw-r--r--  1 user  group  125M  Jun 16 19:00  gestion-cimetiere_0.1.0_amd64.deb
gestion-cimetiere_0.1.0_amd64.deb: Debian binary package
```

## Installation utilisateur final

### 1. Télécharger le .deb

L'utilisateur télécharge `gestion-cimetiere_0.1.0_amd64.deb` depuis le serveur de distribution.

### 2. Installation simple

**Via gestionnaire graphique :**

```bash
# Double-cliquer sur le fichier .deb dans le gestionnaire de fichiers
# Le système installera automatiquement
```

**Via ligne de commande :**

```bash
sudo apt install ./gestion-cimetiere_0.1.0_amd64.deb
```

### 3. Vérifier l'installation

```bash
dpkg -l | grep gestion-cimetiere
which gestion-cimetiere
gestion-cimetiere --version  # Si disponible dans le binaire
```

### 4. Lancer l'application

**Depuis le menu :**
- L'application apparaît automatiquement dans le menu Applications

**Depuis le terminal :**

```bash
gestion-cimetiere
```

L'application se lance avec toutes les dépendances système satisfaites.

## Dépendances système

### Déclarer les dépendances

Tauri détecte automatiquement les dépendances requises (webkit2gtk, etc.). Pour MVP-23, les dépendances courantes incluent :

- `libwebkit2gtk-4.1-0` — Moteur de rendu web
- `libssl3` — Support SSL/TLS
- `libxdo3` — Support X11

Ces dépendances sont déclarées automatiquement dans le paquet .deb généré.

### Vérifier les dépendances déclarées

```bash
dpkg -I target/release/bundle/deb/gestion-cimetiere_*.deb | grep Depends
```

Exemple de sortie :

```
Depends: libwebkit2gtk-4.1-0, libssl3, libxdo3, libc6 (>= 2.29)
```

## Chemins de stockage des données

### Linux (.deb)

Identique à AppImage, respectant XDG Base Directory :

- **Base de données SQLite** : `$XDG_DATA_HOME/gestion-cimetiere/db.db`
  - Défaut : `~/.local/share/gestion-cimetiere/db.db`
- **Sauvegardes** : `~/.local/share/gestion-cimetiere/backups/`
- **Logs** : `~/.local/share/gestion-cimetiere/logs/`
- **Configuration** : `~/.config/gestion-cimetiere/` (si applicable)

**Exemple complet :**

```
~/.local/share/gestion-cimetiere/
├── db.db
├── backups/
│   └── backup_20260616_143022_123456789.db
└── logs/
```

**Avantage :** Données persistent lors de mises à jour (dépôt utilisateur, pas dans `/usr/share/`)

## Compatibilité Debian/Ubuntu

### Distributions supportées

✅ **Testées/Supportées :**
- Ubuntu 18.04+ LTS (Bionic+)
- Ubuntu 20.04 LTS (Focal) — recommandée
- Ubuntu 22.04 LTS (Jammy)
- Debian 10 (Buster)
- Debian 11 (Bullseye) — recommandée
- Debian 12 (Bookworm)
- Linux Mint 19.x+
- Elementary OS 5.x+

✅ **Architecture CPU supportée :**
- x86_64 (64-bit) — par défaut, compilé ici
- arm64 — avec cross-compilation
- armhf — possible avec configuration

### Anciennes distributions

⚠️ **Ubuntu 16.04 LTS (Xenial)** et antérieures :
- Glibc trop ancien (< 2.27)
- Solution : Utiliser AppImage à la place, ou mise à jour OS obligatoire

## Mises à jour

### Mise à jour via apt

Une fois installé, l'application peut être mise à jour facilement si fourni via dépôt.

```bash
# Vérifier les mises à jour disponibles
sudo apt update
sudo apt upgrade gestion-cimetiere

# Ou directement
sudo apt install --only-upgrade gestion-cimetiere
```

### Installation depuis un nouveau .deb

Pour MVP, les utilisateurs téléchargent manuellement un nouveau .deb :

```bash
sudo apt install ./gestion-cimetiere_0.2.0_amd64.deb
```

Apt détecte la nouvelle version et met à jour les fichiers applicatifs.

### Données persistantes

✅ Les données utilisateur restent intactes lors de la mise à jour (stockées dans `~/.local/share/`, pas dans `/usr/share/`)

## Distribution et hébergement

### Via dépôt Debian personnalisé (post-MVP)

Pour une distribution professionnelle, héberger un dépôt Debian avec clés GPG :

```bash
# Exemple structure
deb https://releases.gestion-cimetiere.fr focal main
```

### Via GitHub Releases (MVP)

```bash
gh release create v0.1.0 target/release/bundle/deb/gestion-cimetiere_*.deb
```

Utilisateurs :
1. Téléchargent le `.deb`
2. Install via `apt install ./gestion-cimetiere_*.deb`

## Dépannage

### Erreur : "dpkg: error processing package"

**Cause :** Dépendances système manquantes ou incompatibles

**Solution :**

```bash
# Installer les dépendances automatiquement
sudo apt install --fix-broken
sudo apt install -f
```

### Erreur : "E: Could not open lock file"

**Cause :** Permissions insuffisantes

**Solution :** Utiliser `sudo`

```bash
sudo apt install ./gestion-cimetiere_*.deb
```

### Application ne démarre pas après install

**Cause :** Dépendances binaires manquantes (webkit2gtk, SSL, etc.)

**Solution :** Vérifier dépendances

```bash
ldd /usr/bin/gestion-cimetiere
# ou
dpkg -S $(ldd /usr/bin/gestion-cimetiere | grep "not found")
```

### Fichier /usr/share/applications/gestion-cimetiere.desktop non trouvé

**Cause :** Fichier desktop fourni par Tauri n'a pas été généré

**Solution :** Créer manuellement (file `.desktop`) — Tauri génère automatiquement

```bash
ls /usr/share/applications/gestion-cimetiere*
```

## Configuration avancée .deb (post-MVP)

### Ajouter des scripts d'installation/désinstallation

Tauri permet de configurer des scripts preinst, postinst, prerm, postrm pour customiser le comportement.

### Ajouter des fichiers de configuration système

- Scripts dans `/etc/init.d/` (systemd)
- Fichiers dans `/etc/gestion-cimetiere/`
- Fichiers dans `/usr/share/doc/gestion-cimetiere/`

### Signature GPG des paquets

Pour un dépôt officiel, signer les paquets .deb avec une clé GPG.

## Prochaines étapes

- **MVP-26** : Tests E2E incluant vérification .deb fonctionnel
  - Installation via `apt install`
  - Vérification chemin de stockage des données
  - Test sauvegarde/restauration post-install

- **CI/CD** : Générer .deb automatiquement
  - GitHub Actions sur Linux runner (Ubuntu)
  - Auto-upload vers GitHub Releases
  - Tag pour version sémantique (v0.1.0, v0.2.0, etc.)

- **Post-MVP** :
  - Créer dépôt Debian officiel avec GPG
  - Soumettre à dépôts Ubuntu/Debian officiels
  - Intégrer systemd services si nécessaire
  - Chiffrement stockage données (optionnel)

## Ressources

- [Documentation Tauri 2.x Bundle — Linux deb](https://tauri.app/docs/guides/distribution/)
- [Manuel Debian Packaging](https://www.debian.org/doc/manuals/debian-faq/pkg-basics.en.html)
- [Ubuntu Packaging Guide](https://wiki.ubuntu.com/PackagingGuide)
- [dpkg Man Page](https://manpages.debian.org/dpkg)
- [APT User's Manual](https://manpages.debian.org/apt.8)
- [XDG Base Directory](https://specifications.freedesktop.org/basedir-spec/)
