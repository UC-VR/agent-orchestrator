# Orchestrator Memory (append-only, dated entries)

## 2026-08-28
- Rolled out the launcher-family memory scaffold across the fleet (agent-orchestrator,
  agent-sysadmin, agent-lawyer, agent-bugalteris): every domain launcher now add-dirs its
  home repo, personas read MEMORY/JOURNAL/BACKLOG (+ domain dirs) at session start when
  home is reachable, and append learnings back at session end (append-only, dated,
  commit+push ff-only). Memory files are `merge=union` in `.gitattributes` so appends
  from all 3 machines auto-merge without conflicts.
