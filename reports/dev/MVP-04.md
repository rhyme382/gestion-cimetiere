# MVP-04 — Définir le schéma SQLite MVP et les entités cœur

**Date :** 2026-06-15  
**Agent :** backend  
**Statut :** En cours de définition  
**Dépend de :** MVP-01  

## Objectif

Concevoir le modèle de données minimal pour le MVP en définissant les tables, relations et contraintes nécessaires pour gérer les cimetières, emplacements, concessions, personnes et défunts.

## Entités cœur MVP

1. **cemeteries** — Cimetières d'une ou plusieurs communes
2. **plots** — Emplacements (cases) du cimetière
3. **concessions** — Droits de concession avec dates (acquisition, renouvellement, échéance)
4. **individuals** — Personnes physiques (concessionnaires, ayants droit, défunts)
5. **burials** — Associations défunt ↔ concession ↔ emplacement

## Tâches clés

- [ ] Définir les tables et leurs colonnes
- [ ] Établir les relations, contraintes et indices
- [ ] Rédiger les migrations initiales (schema + seed data)
- [ ] Valider la cardinalité et la normalisation
- [ ] Documenter les choix de types et de contraintes

## Schéma proposé (aperçu)

```sql
CREATE TABLE cemeteries (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  commune TEXT,
  capacity INTEGER,
  created_at TEXT,
  updated_at TEXT
);

CREATE TABLE plots (
  id INTEGER PRIMARY KEY,
  cemetery_id INTEGER NOT NULL REFERENCES cemeteries(id),
  section TEXT,
  row INTEGER,
  number INTEGER,
  capacity INTEGER DEFAULT 1,
  status TEXT, -- "available", "occupied", "reserved", etc.
  created_at TEXT,
  updated_at TEXT
);

CREATE TABLE concessions (
  id INTEGER PRIMARY KEY,
  cemetery_id INTEGER NOT NULL REFERENCES cemeteries(id),
  plot_id INTEGER REFERENCES plots(id),
  acquired_at TEXT,
  expires_at TEXT,
  renewed_at TEXT,
  status TEXT, -- "active", "expired", "abandoned", etc.
  created_at TEXT,
  updated_at TEXT
);

CREATE TABLE individuals (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT,
  phone TEXT,
  role TEXT, -- "concessionnaire", "heir", "deceased", etc.
  created_at TEXT,
  updated_at TEXT
);

CREATE TABLE burials (
  id INTEGER PRIMARY KEY,
  concession_id INTEGER NOT NULL REFERENCES concessions(id),
  individual_id INTEGER NOT NULL REFERENCES individuals(id),
  buried_at TEXT,
  created_at TEXT,
  updated_at TEXT
);
```

## Fichiers à créer / modifier

- `src-tauri/migrations/` (dossier)
- `src-tauri/migrations/001_initial_schema.sql`
- `src-tauri/migrations/002_seed_data.sql` (optionnel pour MVP)
- Modèles Rust correspondants

## Décisions architecturales

À documenter lors de l'implémentation :
- Stratégie de soft delete vs hard delete
- Gestion des timestamps (UTC, timezone)
- Approche pour les états (enum vs string)
- Indexation pour les recherches critiques

## Problèmes connus

- À valider : gestion des droits d'accès (hors MVP, mais à prévoir)
- À valider : gestion des archivages historiques (hors MVP, mais à prévoir)

## Résultats des tests

À compléter lors de l'implémentation.

## Prochaines étapes

1. Valider le schéma avec le mapping (MVP-07) et le frontend (MVP-02)
2. Lancer MVP-05 : Définir les contrats API/Tauri et les DTO partagés
3. Lancer MVP-09 : Implémenter les migrations initiales et les fixtures MVP
