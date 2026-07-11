# Rapport agents — 2026-07-11 orchestrator foundation

## Décisions

- Le nouveau socle d'orchestration vit sous `orchestrator/` et laisse `orchestration/` intact comme archive du prototype CrewAI.
- Les runners externes sont testés uniquement par injection de mocks, sans exécution de binaires réels.
- Le contrat backlog initial est un JSON atomique versionné contenant une liste de `Task` Pydantic.
- Le point de persistance d'exécution retenu pour LangGraph est un checkpoint SQLite configurable par la CLI.
