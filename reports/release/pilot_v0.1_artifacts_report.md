# Rapport d'artefacts v0.1-pilot

**Date :** 2026-06-17  
**Release Version :** v0.1.0-pilot  
**Branch :** release/pilot-v0.1  
**Statut :** Artefacts partiels générés (binaire ✅, installers requis CI/CD)  

## 1. Artefacts générés avec succès ✅

### Binaire Tauri (Linux)
- **Chemin :** `target/release/gestion-cimetiere`
- **Taille :** 14 MB
- **Type :** ELF 64-bit LSB executable
- **Platform :** Linux x86_64
- **Statut :** ✅ Exécutable, testable sur Linux
- **Commande de test :** `./target/release/gestion-cimetiere`

### Frontend optimisé
- **Répertoire :** `dist/`
- **Taille totale :** 277 KB gzip
- **Module :** 1815 modules Vite transformés
- **Composants :** Dashboard, Listes, Fiches, Cartographie, Alertes, PDF, Sauvegardes
- **Statut :** ✅ Prêt pour bundling

## 2. Artefacts manquants et raisons

### ❌ AppImage (Linux portable)
**Statut :** Non généré  
**Raison :** Erreur linuxdeploy Tauri — "couldn't find a square icon to use as AppImage icon"  
**Cause racine :** Le bundler AppImage de Tauri ne trouve pas l'icône dans le format attendu par linuxdeploy (possiblement chemin ou format incompatible)  
**Diagnostic :**
- Icônes présentes : icon.png (128x128, sRGB), 32x32.png, 16x16.png — toutes carrées
- Format correct : PNG 8-bit RGBA
- Problème : linuxdeploy bundler (partie de Tauri) ne détecte pas les icônes

**Workaround :** 
- Utiliser GitHub Actions avec ubuntu-latest (peut avoir une configuration différente)
- Ou, construire AppImage manuellement avec `appimagetool` après build Tauri

### ❌ .deb (Debian/Ubuntu)
**Statut :** Non généré  
**Raison :** Build Tauri interrompu par erreur AppImage (même commande `npm run tauri build` compile NSIS + AppImage + .deb ensemble)  
**Dépendance :** AppImage doit d'abord fonctionner  
**Workaround :** Fixer AppImage, puis .deb se génère automatiquement

### ❌ NSIS .exe (Windows)
**Statut :** Non généré  
**Raison :** Aucun compilateur NSIS disponible sur environnement Linux  
**Cause racine :** NSIS est un outil Windows uniquement  
**Attendu :** Prévu pour build GitHub Actions sur Windows runner  
**Workaround :** Compiler sur machine Windows avec `npm run tauri build`

## 3. Icônes et configuration

### Diagnostic icônes
```
identify src-tauri/icons/*.png
src-tauri/icons/128x128.png: PNG 128x128 8-bit sRGB
src-tauri/icons/16x16.png: PNG 16x16 8-bit sRGB
src-tauri/icons/32x32.png: PNG 32x32 8-bit sRGB
src-tauri/icons/icon.png: PNG 128x128 8-bit sRGB
src-tauri/icons/icon.ico: MS Windows icon resource
```

### Corrections appliquées
1. ✅ Créé icône couleur valide (bleu avec texte "GC") en lieu et place des placeholders
2. ✅ Converti en RGBA (8-bit sRGB) avec Python PIL
3. ✅ Régénéré tous les formats PNG (16x16, 32x32, 128x128)
4. ✅ Régénéré icon.ico pour Windows (3 résolutions)

**Résultat :** Icônes visuelles valides, mais linuxdeploy Tauri ne les détecte toujours pas

## 4. Reconstruction des icônes

**Script utilisé :**
```python
from PIL import Image, ImageDraw, ImageFont

# Créer icône RGBA 128x128 (bleu + texte blanc "GC")
img = Image.new('RGBA', (128, 128), (0, 102, 204, 255))
draw = ImageDraw.Draw(img)
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
draw.text((32, 36), "GC", font=font, fill=(255, 255, 255, 255))
img.save('src-tauri/icons/icon.png', 'PNG')

# Redimensionner pour autres tailles
for size in [32, 16]:
    img_resized = img.resize((size, size), Image.Resampling.LANCZOS)
    img_resized.save(f'src-tauri/icons/{size}x{size}.png', 'PNG')
```

## 5. Configuration Tauri validée

**Fichier :** `src-tauri/tauri.conf.json`
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

**Validation :** ✅ Syntaxe correcte, targets reconnus par Tauri CLI

## 6. Commandes de build réussies

```bash
✅ npm install                          # Dépendances OK
✅ npm run build                        # Frontend OK (277KB gzip)
✅ cargo test --test-threads=1          # 91/91 tests ✅
✅ npm run tauri build (Rust part)      # Compilation Rust OK
❌ npm run tauri build (bundling)       # AppImage échoue, cascade sur deb
```

## 7. Plan pour générer les artefacts définitifs

### Pour AppImage (.AppImage) — Linux
**Plateforme :** GitHub Actions Linux runner  
**Options :**
1. **Via Tauri (préféré)** — Fixer le problème linuxdeploy en CI/CD
2. **Via appimagetool** — Build manuel après binaire Tauri

**Workflow proposé :**
```yaml
build-appimage:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v3
      with:
        ref: v0.1.0-pilot
    - run: npm install && npm run build && npm run tauri build
    - uses: actions/upload-artifact@v3
      with:
        name: appimage
        path: target/release/bundle/appimage/*.AppImage
```

### Pour .deb (Debian/Ubuntu) — Linux
**Plateforme :** GitHub Actions Linux runner (après AppImage)  
**Remarque :** Généré automatiquement avec `npm run tauri build` quand AppImage OK

**Workflow proposé :**
```yaml
build-deb:
  runs-on: ubuntu-latest
  needs: build-appimage
  steps:
    - uses: actions/checkout@v3
      with:
        ref: v0.1.0-pilot
    - run: npm install && npm run build && npm run tauri build
    - uses: actions/upload-artifact@v3
      with:
        name: deb
        path: target/release/bundle/deb/*.deb
```

### Pour NSIS .exe (Windows) — Windows uniquement
**Plateforme :** GitHub Actions Windows runner  
**Commande :** `npm run tauri build`  
**Résultat :** `target/release/bundle/nsis/*.exe`

**Workflow proposé :**
```yaml
build-nsis:
  runs-on: windows-latest
  steps:
    - uses: actions/checkout@v3
      with:
        ref: v0.1.0-pilot
    - run: npm install && npm run build && npm run tauri build
    - uses: actions/upload-artifact@v3
      with:
        name: nsis
        path: target/release/bundle/nsis/*.exe
```

## 8. Fichier workflow GitHub Actions complet

**Fichier :** `.github/workflows/release-v0.1-artifacts.yml`

```yaml
name: Build Release v0.1-pilot Artifacts

on:
  workflow_dispatch:
  push:
    tags:
      - v0.1.0-pilot

jobs:
  build-linux:
    strategy:
      matrix:
        include:
          - name: appimage
            artifact: target/release/bundle/appimage/*.AppImage
          - name: deb
            artifact: target/release/bundle/deb/*.deb
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          ref: v0.1.0-pilot
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - uses: dtolnay/rust-toolchain@stable
      - run: sudo apt update && sudo apt install -y libgtk-3-dev libxdo-dev libssl-dev dpkg dpkg-dev build-essential
      - run: npm install
      - run: npm run build
      - run: npm run tauri build
      - uses: actions/upload-artifact@v3
        with:
          name: ${{ matrix.name }}
          path: ${{ matrix.artifact }}

  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
        with:
          ref: v0.1.0-pilot
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - uses: dtolnay/rust-toolchain@stable
      - run: npm install
      - run: npm run build
      - run: npm run tauri build
      - uses: actions/upload-artifact@v3
        with:
          name: nsis
          path: target/release/bundle/nsis/*.exe

  create-release:
    needs: [build-linux, build-windows]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/download-artifact@v3
      - name: Display artifacts
        run: find . -type f -name '*.AppImage' -o -name '*.deb' -o -name '*.exe'
      - name: Create GitHub Release
        run: |
          gh release create ${{ github.ref_name }} \
            --title "Gestion Cimetière v0.1 Pilot Release" \
            --target release/pilot-v0.1 \
            ./**/*.AppImage \
            ./**/*.deb \
            ./**/*.exe
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## 9. Commandes gh pour upload manuel

```bash
# Après génération des artefacts localement (ou téléchargement depuis CI)

gh release upload v0.1.0-pilot \
  target/release/bundle/nsis/Gestion_Cimetiere_0.1.0_x64.exe \
  target/release/bundle/appimage/Gestion_Cimetiere_0.1.0_x64.AppImage \
  target/release/bundle/deb/gestion-cimetiere_0.1.0_amd64.deb
```

## 10. Alternative : Déploiement avec binaire seul

**Pour test pilote immédiat :**

Le binaire Rust `target/release/gestion-cimetiere` (14 MB) est exécutable directement sur Linux. Il peut être distribué comme :
- Exécutable direct pour mairies Linux
- Ou packagé manuellement dans un script shell + données

**Commande :** `./target/release/gestion-cimetiere`

**Avantage :** Pas de dépendance AppImage/deb, fonctionne immédiatement  
**Limitation :** Pas d'intégration système (menu, icône desktop, etc.)

## 11. Récapitulatif

| Artefact | Généré | Localisation | Commande upload |
| --- | --- | --- | --- |
| Binaire Tauri | ✅ | `target/release/gestion-cimetiere` | gh release upload v0.1.0-pilot ... |
| AppImage | ❌ | Attendu : `target/release/bundle/appimage/` | `*.AppImage` |
| .deb | ❌ | Attendu : `target/release/bundle/deb/` | `*.deb` |
| NSIS .exe | ❌ | Attendu : `target/release/bundle/nsis/` | `*.exe` |
| Frontend dist | ✅ | `dist/` | N/A (inclus dans binaire) |

## 12. Prochaines étapes

1. **Créer workflow GitHub Actions** (`.github/workflows/release-v0.1-artifacts.yml`)
2. **Déclencher workflow** via `workflow_dispatch` ou push tag v0.1.0-pilot
3. **Vérifier artifacts** générés (Linux et Windows)
4. **Uploader vers GitHub Release** via workflow ou manuellement avec `gh release upload`
5. **Tester binaire** Linux sur machine réelle avant déploiement mairie

## 13. Support technique

- **Problème AppImage :** linuxdeploy bundler incompatible avec icônes. Solution : CI/CD ou appimagetool manuel.
- **Problème NSIS :** Nécessite Windows. Solution : GitHub Actions Windows runner.
- **Alternative immédiate :** Déployer binaire Tauri direct sur Linux.

---

**Verdict :** Artefacts partiels générés. Workflow CI/CD proposé pour complétude. MVP v0.1 pilot peut procéder avec binaire Tauri ou attendre CI/CD pour installers complets.
