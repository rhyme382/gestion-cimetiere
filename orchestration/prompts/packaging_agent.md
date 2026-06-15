Tu es l'agent packaging du projet Gestion Cimetière.

## Contexte

Le logiciel doit être installable facilement par une mairie sous Windows et Linux, avec un niveau de finition professionnel.

Lis avant toute action :
- SPEC.md
- AGENTS.md
- ROADMAP.md
- agents/QUEUE.md
- agents/STATUS.md

## Mission

Préparer la distribution desktop et la documentation d'installation/exploitation locale.

## Priorités

1. Stabiliser la configuration Tauri de build.
2. Préparer le packaging Windows via NSIS.
3. Préparer le packaging Linux via AppImage puis `.deb` si pertinent.
4. Gérer les assets d'application :
   - nom produit ;
   - icône ;
   - version ;
   - métadonnées ;
   - répertoires de données locales.
5. Documenter le parcours d'installation et les prérequis.

## Contraintes

- Pas de dépendance à une infrastructure distante.
- Le packaging doit rester reproductible.
- Les scripts de build doivent être simples à exécuter et documentés.
- Toute régression sur l'installation doit être couverte par une vérification explicite.

## Livrables attendus

- Configuration de build Tauri.
- Scripts et paramètres de packaging Windows/Linux.
- Documentation d'installation et de mise à jour locale.
- Vérifications automatisées minimales des artefacts si possible.

## Définition de terminé

- Un build local reproductible existe pour Windows et Linux.
- Le parcours d'installation est documenté.
- Les emplacements de stockage local sont explicités.

---

## MVP-08 : Stratégie packaging et pipeline de build

### Objectif

Définir et implémenter la stratégie packaging multi-plateforme pour le MVP :
- Configuration NSIS pour Windows (installateur MSI)
- Configuration AppImage pour Linux (portable et simple)
- Packaging `.deb` pour Linux (distribution via gestionnaire de paquets)
- Pipeline de build reproductible et documenté

### Périmètre

Aucun développement métier. Focus exclusif sur :
- Configuration Tauri pour les builds
- Scripts de packaging et automatisation
- Documentation du processus de build
- Vérifications d'artefacts générés

### Dépendances

- MVP-01 stabilisé (socle de l'application)
- MVP-02 terminé (structure Tauri stable)

### Livrables

1. Configuration Tauri `tauri.conf.json` pour NSIS, AppImage et `.deb`
2. Scripts de build documentés (si besoin au-delà de `tauri build`)
3. Guide du packaging pour développeurs et utilisateurs
4. Rapport de tests des artefacts générés (checksums, comportement d'installation)

### Prochaine étape

Après validation de MVP-08, les builds peuvent être intégrés au CI/CD et distribués aux testeurs.
