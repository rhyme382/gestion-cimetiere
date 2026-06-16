# Revue de readiness MVP-21

Date : 2026-06-16
Agent : orchestrator
Statut : audit post-livraison, sans modification applicative

## Objet

Vérifier MVP-21 selon les critères demandés :

- `reports/dev/MVP-21.md`
- `agents/STATUS.md`
- configuration Tauri / NSIS
- commits récents
- absence de modification métier
- possibilité d’enchaîner sur MVP-22

## Rapports et statut

Présents :

- `reports/dev/MVP-21.md`
- `agents/STATUS.md`

Constat :

- `reports/dev/MVP-21.md` documente bien le périmètre packaging Windows NSIS, les fichiers touchés, les validations et les limites ;
- `agents/STATUS.md` marque MVP-21 comme livré, fait progresser la phase 5, et positionne MVP-22 comme prochain lot packaging.

## Commit MVP-21

Commit principal identifié :

- `d849a46` — `feat(packaging): implement MVP-21 Windows NSIS configuration`

Périmètre du commit :

- `agents/STATUS.md`
- `docs/PACKAGING_WINDOWS.md`
- `reports/dev/MVP-21.md`
- `src-tauri/icons/16x16.png`
- `src-tauri/icons/icon.ico`
- `src-tauri/tauri.conf.json`

Conclusion :

- le lot est bien limité à la configuration packaging, aux assets d’icône et à la documentation ;
- aucun fichier frontend React/TypeScript n’est modifié ;
- aucun fichier backend métier Rust n’est modifié.

## Configuration Tauri / NSIS

Contrôles observés dans `src-tauri/tauri.conf.json` :

- `productName` : `Gestion Cimetière`
- `version` : `0.1.0`
- `identifier` : `com.gestion-cimetiere.app`
- `bundle.active` : `true`
- `bundle.targets` : `["nsis"]`

Conclusion :

- la configuration Tauri est cohérente avec un packaging Windows NSIS minimal ;
- la cible NSIS est explicitement activée ;
- les métadonnées applicatives requises pour le bundling sont présentes.

## Assets Windows

Contrôle observé :

- `src-tauri/icons/icon.ico` existe et est détecté comme ressource d’icône Windows ;
- `src-tauri/icons/16x16.png` existe ;
- le dépôt contient donc les assets minimaux annoncés par le rapport.

## Documentation packaging

Contrôle observé :

- `docs/PACKAGING_WINDOWS.md` existe et couvre :
  - prérequis ;
  - étapes de build ;
  - limites de build NSIS hors Windows ;
  - métadonnées ;
  - dépannage.

Réserve mineure :

- le guide parle par endroits de “paquet d'installation Windows (.msi)” alors que la cible configurée est `nsis`, qui génère un installateur `.exe`.
- cette imprécision est documentaire, pas bloquante pour la readiness de la configuration.

## Absence de modification métier

Conclusion :

- confirmée.

Le commit MVP-21 ne touche ni :

- `src-tauri/src/**` côté logique métier/backend ;
- `src/**` côté frontend ;
- ni les modèles, repositories, commandes Tauri métier ou services applicatifs.

## Validation technique réellement démontrée

Éléments observables :

- la configuration JSON est valide structurellement ;
- le ciblage `nsis` est explicite ;
- les assets d’icônes sont présents ;
- la limitation “build final NSIS sur Windows uniquement” est documentée et cohérente.

Limite assumée :

- aucun build NSIS complet sous Windows n’a été exécuté dans cet audit ;
- MVP-21 reste donc une **préparation de packaging**, pas une preuve d’installateur Windows final généré ici.

Cette limite reste cohérente avec l’objectif déclaré de MVP-21.

## MVP-22 peut-il démarrer ?

Oui.

Justification :

- la roadmap fixe `MVP-22` à la préparation Linux AppImage ;
- les dépendances déclarées sont satisfaites (`MVP-02` et `MVP-20`) ;
- MVP-21 met en place la base packaging Windows sans introduire de blocage sur la suite Linux ;
- `agents/STATUS.md` est cohérent avec un lancement de `MVP-22` ensuite.

## Décision finale

**MVP21_ACCEPTED**

## Motif principal

Le lot livre bien ce qu’il annonce :

- configuration Tauri orientée NSIS ;
- métadonnées applicatives correctes ;
- assets Windows présents ;
- documentation de build fournie ;
- aucun impact métier ni frontend.

Les réserves restantes sont mineures et documentaires, sans remettre en cause le démarrage de MVP-22.
