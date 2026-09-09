# Backlog (append-only)

- ccs: supercharged orchestrator v2 — review instructions/tools for Claude 5-series
  models, de-bloat (VR feedback pending)
- Phase 2: user-scope MCP/plugin slimming
- Phase 3: ccy+ basics profile files
- Validate scout-readonly-gate against a real scout PreToolUse payload (agent_id/agent_type presence); if absent, fall back to frontmatter-scoped hook in scout.md
- README self-learning section documents hooks/session-start-skill-review.sh which does not exist in hooks/ — reconcile
- Review judge-offer acceptance rate after ~2 weeks via session-journal spawns line; tune trigger if never accepted or always accepted
- lp: Shift+Enter under Herdr (herdr#3269) — pick fix A/B/C from HANDOVER-2026-09-07 addendum 2; if A, remove WT shift+enter binding in live + chezmoi .tmpl and set TERM=xterm-kitty in the claude launcher under Herdr
- 2026-09-10: execute PLAN-declutter-vr-oc1-2026-09-10.md phases A–E (dry-run first); then run the same three scout briefs on lp-ryckov11 and ix-claude1
- 2026-09-10: scout brief template — add `ls` of container dirs + hand docker/systemctl to a worker (scout gate blocks them)
- 2026-09-10: fix auto-memory drift in ~/.claude/projects/-home-vr/memory: skills count 195→50, Honcho plugin disabled
