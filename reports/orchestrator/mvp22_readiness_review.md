# Revue de readiness MVP-22

Date : 2026-06-16
Agent : orchestrator
Statut : audit post-livraison, sans modification applicative

## Objet

Vérifier MVP-22 selon les critères demandés :

- `reports/dev/MVP-22.md`
- `agents/STATUS.md`
- configuration Tauri AppImage
- absence de conflit avec NSIS MVP-21
- absence de modification métier
- possibilité de démarrer MVP-23 ensuite

## Rapports et statut

Présents :

- `reports/dev/MVP-22.md`
- `agents/STATUS.md`

Constat :

- `reports/dev/MVP-22.md` documente correctement le périmètre AppImage, les décisions, les validations et les limites ;
- `agents/STATUS.md` marque MVP-22 comme livré et positionne MVP-23 comme prochain lot packaging.

## Commit MVP-22

Commit principal identifié :

- `6afdec8` — `feat(packaging): implement MVP-22 Linux AppImage configuration`

Fichiers inclus dans ce commit :

- `AGENTS.md`
- `agents/STATUS.md`
- `docs/PACKAGING_LINUX_APPIMAGE.md`
- `reports/dev/MVP-22.md`
- `reports/orchestrator/mvp21_readiness_review.md`
- `src-tauri/tauri.conf.json`

Analyse :

- le seul fichier de configuration packaging réellement touché est `src-tauri/tauri.conf.json` ;
- les autres fichiers sont documentaires ou de contexte ;
- aucun fichier frontend React/TypeScript n’est modifié ;
- aucun fichier backend métier Rust n’est modifié.

Réserve :

- le commit emporte deux fichiers non directement liés au lot (`AGENTS.md`, `reports/orchestrator/mvp21_readiness_review.md`) ;
- cela n’introduit pas de modification métier, mais le commit n’est pas totalement propre en périmètre.

## Configuration Tauri AppImage

Contrôle observé dans `src-tauri/tauri.conf.json` :

- `bundle.active` : `true`
- `bundle.targets` : `["nsis", "appimage"]`
- `identifier` : `com.gestion-cimetiere`

Conclusion :

- la cible AppImage est bien activée ;
- la configuration est multi-cible et cohérente avec l’objectif Linux ;
- la correction d’identifiant vers `com.gestion-cimetiere` est compatible avec Linux et n’empêche pas NSIS.

## Conflit avec NSIS MVP-21

Évaluation : **pas de conflit technique bloquant identifié**.

Points validés :

- `nsis` reste présent dans `bundle.targets` ;
- `appimage` est ajouté sans retirer la cible Windows ;
- la stratégie multi-cible Tauri est cohérente ;
- les assets Windows (`icon.ico`) ne sont pas supprimés ;
- la documentation Windows existe toujours.

Réserve documentaire :

- `docs/PACKAGING_WINDOWS.md` contient encore l’ancien `identifier` `com.gestion-cimetiere.app` dans son tableau de métadonnées ;
- cela crée une légère incohérence documentaire avec `tauri.conf.json`, sans casser la configuration réelle.

## Absence de modification métier

Conclusion :

- confirmée.

Le lot ne touche ni :

- `src-tauri/src/**` côté logique métier/backend ;
- `src/**` côté frontend ;
- ni les commandes Tauri métier, repositories, services applicatifs ou DTO.

## Validation technique réellement démontrée

Éléments observables :

- `tauri.conf.json` inclut bien `appimage` ;
- la documentation Linux AppImage est présente et détaillée ;
- `reports/dev/MVP-22.md` documente correctement le fait que la préparation est validée, avec limites explicites sur le build complet ;
- la coexistence avec NSIS est maintenue par la configuration multi-cible.

Limite importante :

- aucune preuve directe d’un artefact `.AppImage` généré n’est fournie par cet audit ;
- MVP-22 reste donc une **préparation/configuration AppImage**, pas une démonstration d’artefact final produit ici.

Cette limite reste cohérente avec le périmètre documenté du lot.

## MVP-23 peut-il démarrer ?

Oui.

Justification :

- la roadmap fixe `MVP-23` à la préparation du packaging Linux `.deb` ;
- `MVP-22` stabilise la configuration Linux et la documentation AppImage ;
- `agents/STATUS.md` positionne correctement `MVP-23` comme prochain lot ;
- aucune dépendance métier ou frontend nouvelle n’est introduite.

## Décision finale

**MVP22_ACCEPTED**

## Motif principal

Le lot livre bien ce qu’il annonce :

- activation AppImage dans Tauri ;
- maintien de la coexistence avec NSIS ;
- documentation Linux AppImage fournie ;
- aucune modification métier ni frontend.

Les réserves restantes sont de propreté de commit et de cohérence documentaire mineure, sans remettre en cause le démarrage de MVP-23.
