# Rapport agents — 2026-07-11 orchestrator product audit

## Decisions

- La commande `audit` lance desormais un vrai workflow produit distinct du graphe LangGraph de dispatch.
- Le backlog produit officiel est valide via `Pydantic` avec controle des dependances, des IDs et de l'observabilite minimale.
- `codex exec` reste confine en `workspace-write` et toute modification hors livrables d'audit est detectee par comparaison Git avant/apres.
- Les anciens livrables d'audit ne sont jamais ecrases silencieusement ; `--force` archive d'abord les fichiers precedents.
