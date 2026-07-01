#!/usr/bin/env bash
# SessionEnd hook: append-only per-session journal + skill-update marker. Non-blocking. Always exit 0.
set -uo pipefail
input=$(cat 2>/dev/null || true)
parsed=$(printf '%s' "$input" | node -e '
  let d="";process.stdin.on("data",c=>d+=c).on("end",()=>{
    let o={};try{o=JSON.parse(d)}catch(e){}
    const f=k=>String(o[k]??"").replace(/[\t\r\n]/g," ");
    process.stdout.write([f("session_id"),f("cwd"),f("reason"),f("transcript_path")].join("\t"));
  });' 2>/dev/null)
IFS=$'\t' read -r session_id cwd reason transcript_path <<< "$parsed"
[ -z "$cwd" ] && cwd="$PWD"
[ -z "$session_id" ] && session_id="unknown"
date_str=$(date +%Y-%m-%d 2>/dev/null || echo "0000-00-00")
ts=$(date -Iseconds 2>/dev/null || echo "")
journal_dir="$cwd/.claude/journal"
mkdir -p "$journal_dir" 2>/dev/null || true
journal_file="$journal_dir/${date_str}-${session_id}.md"
{
  printf -- '- session_end %s | reason=%s | session=%s\n' "$ts" "${reason:-other}" "$session_id"
  [ -n "$transcript_path" ] && printf -- '  transcript: %s\n' "$transcript_path"
} >> "$journal_file" 2>/dev/null || true
printf '%s\n' "$date_str $session_id" >> "$cwd/.claude/.skill-update-pending" 2>/dev/null || true
exit 0
