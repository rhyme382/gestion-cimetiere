# Archivage de l'ancienne orchestration

L'ancienne couche d'orchestration a été retirée de la branche active lors de la création du nouveau système `autodev`.

Elle reste accessible dans Git au tag :

`before-autodev-rebuild`

Motifs de la reconstruction :

- backlog trop rigide ;
- modèles Pydantic trop figés ;
- architecture développée progressivement autour des anciens MVP ;
- besoin d'une chaîne simple fondée sur LangGraph, Codex et Claude Code.

Le code métier React, Rust et Tauri n'est pas concerné par cet archivage.
