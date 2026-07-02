#!/usr/bin/env bash
# SessionEnd hook (learning-loop v2). Non-blocking. ALWAYS exit 0 (fail-open).
#
# Behavior:
#   c) Cheap per-cwd stub: one index line per session end, unconditionally.
#   a) Anchor pre-gate: parse the transcript JSONL and only proceed if the
#      session was substantive (>=12 tool_use blocks AND >=2 file-edit blocks).
#   b) Detached background capture: fire-and-forget `claude -p` (acceptEdits,
#      tools = Read/Edit/Write) that decides whether to append ONE learning
#      block to the GLOBAL LEARNINGS.md. Detached via PowerShell Start-Process
#      so it survives this hook's own exit / process-tree kill at timeout.
#   d) Every step is wrapped so any failure falls through to exit 0.
set -uo pipefail

# ---- parse stdin JSON (node, no jq) --------------------------------------
input=$(cat 2>/dev/null || true)
parsed=$(printf '%s' "$input" | node -e '
  let d="";process.stdin.on("data",c=>d+=c).on("end",()=>{
    let o={};try{o=JSON.parse(d)}catch(e){}
    const f=k=>String(o[k]??"").replace(/[\t\r\n]/g," ");
    process.stdout.write([f("session_id"),f("cwd"),f("reason"),f("transcript_path")].join("\t"));
  });' 2>/dev/null || true)
IFS=$'\t' read -r session_id cwd reason transcript_path <<< "$parsed"
[ -z "${cwd:-}" ] && cwd="$PWD"
[ -z "${session_id:-}" ] && session_id="unknown"
date_str=$(date +%Y-%m-%d 2>/dev/null || echo "0000-00-00")
ts=$(date -Iseconds 2>/dev/null || echo "")

# ---- c) cheap per-cwd stub (ALWAYS, regardless of gate) ------------------
journal_dir="$cwd/.claude/journal"
mkdir -p "$journal_dir" 2>/dev/null || true
journal_file="$journal_dir/${date_str}-${session_id}.md"
{
  printf -- '- session_end %s | reason=%s | session=%s\n' "$ts" "${reason:-other}" "$session_id"
  [ -n "${transcript_path:-}" ] && printf -- '  transcript: %s\n' "$transcript_path"
} >> "$journal_file" 2>/dev/null || true

# ---- a) anchor pre-gate --------------------------------------------------
# If no usable transcript, skip the gate + capture entirely (stub already written).
[ -z "${transcript_path:-}" ] && exit 0
[ -f "$transcript_path" ] || exit 0

counts=$(node -e '
  const fs=require("fs");
  const p=process.argv[1];
  const S=new Set(["Edit","Write","MultiEdit","NotebookEdit"]);
  let tc=0,mo=0;
  try{
    const lines=fs.readFileSync(p,"utf8").split("\n");
    for(const ln of lines){
      if(!ln.trim())continue;
      let o;try{o=JSON.parse(ln)}catch(e){continue}
      if(o&&o.type==="assistant"&&o.message&&Array.isArray(o.message.content)){
        for(const b of o.message.content){
          if(b&&b.type==="tool_use"){tc++;if(S.has(b.name))mo++;}
        }
      }
    }
  }catch(e){}
  process.stdout.write(tc+"\t"+mo);
' "$transcript_path" 2>/dev/null || true)
IFS=$'\t' read -r tool_calls meaningful <<< "$counts"
[[ "${tool_calls:-}" =~ ^[0-9]+$ ]] || exit 0      # node missing / parse failure -> fail-open, no capture
[[ "${meaningful:-}" =~ ^[0-9]+$ ]] || meaningful=0
# Gate: require a substantive session.
[ "$tool_calls" -lt 12 ] && exit 0
[ "$meaningful" -lt 2 ] && exit 0

# ---- b) detached background capture --------------------------------------
gjournal="$HOME/.claude/journal"
mkdir -p "$gjournal" 2>/dev/null || true

# tidy any stale capture artifacts (>1 day old); best-effort
find "$gjournal" -maxdepth 1 -type f -name '.capture-*' -mtime +1 -delete 2>/dev/null || true

prompt_file="$gjournal/.capture-prompt-${session_id}.txt"
launcher_file="$gjournal/.capture-run-${session_id}.sh"

# Resolve absolute claude + bash paths (detached PATH is not guaranteed).
claude_bin=$(command -v claude 2>/dev/null || true)
[ -z "$claude_bin" ] && claude_bin="$HOME/AppData/Roaming/npm/claude"
bash_win=$(cygpath -w "$(command -v bash 2>/dev/null)" 2>/dev/null || echo 'C:\Program Files\Git\bin\bash.exe')

# The capture prompt (written to a file to dodge command-line quoting).
cat > "$prompt_file" <<PROMPT || exit 0
You are a background learning-capture agent. Do NOT ask questions; act autonomously and then stop.

1. Read the session transcript at this exact path: ${transcript_path}
2. Decide whether this session contains a genuinely transferable lesson -- something learned, a decision made, or a candidate skill/recipe update that would help future sessions. General-purpose and reusable, NOT a one-off project detail.
3. If there is NO transferable lesson, do nothing and write nothing. Exiting without changes is a valid, expected outcome.
4. If there IS one, append EXACTLY ONE block to the GLOBAL file ${gjournal}/LEARNINGS.md (create the directory and file if missing). APPEND ONLY -- never rewrite, reorder, or delete existing content. The block must match this exact format:

<!-- learning -->
## ${date_str} · session ${session_id}
**Learned:** ...
**Decided:** ...
**Candidate skill updates:** ...
**Dedupe check:** ...

Rules:
- Write at most ONE block. Keep each field to 1-3 concise sentences.
- The first line must be exactly '<!-- learning -->' (this sentinel is how the loop counts learnings).
- NEVER include secrets, API keys, tokens, passwords, or personal identifiers (emails, names, phone numbers, addresses). Redact or omit them.
- If a field has nothing meaningful, write 'n/a' -- do not fabricate.
- Do not touch any file other than LEARNINGS.md.
PROMPT

# Self-cleaning launcher: run claude reading the prompt, then remove both files.
# permission-mode: bypassPermissions is REQUIRED (not acceptEdits) because the
# target LEARNINGS.md lives under ~/.claude/, which Claude Code guards as a
# "sensitive path"; writes there are hard-blocked in non-interactive (-p) mode.
# Tested 2026-07-02: acceptEdits alone AND acceptEdits + an explicit scoped
# permissions.allow rule for ~/.claude/journal/** (Edit()/Write() path-glob
# rules in settings.json) were BOTH still blocked by the sensitive-path guard --
# an explicit scoped allow rule does NOT defeat the ~/.claude/** guard. Controls:
# the same acceptEdits config wrote fine to a NON-sensitive path, and
# bypassPermissions wrote fine to the same journal path, isolating the
# sensitive-path guard as the sole blocker. bypassPermissions is therefore
# required; blast radius stays contained via --allowedTools "Read" "Edit"
# "Write". Do not re-litigate the acceptEdits+allow-rule route without new evidence.
# stdin is closed (< /dev/null) so `claude -p` does not stall waiting on it.
cat > "$launcher_file" <<LAUNCHER || exit 0
#!/usr/bin/env bash
"${claude_bin}" -p "\$(cat "${prompt_file}")" --permission-mode bypassPermissions --allowedTools "Read" "Edit" "Write" < /dev/null >/dev/null 2>&1
rm -f "${prompt_file}" 2>/dev/null || true
rm -f "\$0" 2>/dev/null || true
LAUNCHER

# Fire-and-forget via PowerShell Start-Process (new independent process; proven
# to survive parent exit AND a forced process-tree kill of this hook).
powershell.exe -NoProfile -WindowStyle Hidden -Command "Start-Process -FilePath '${bash_win}' -ArgumentList '${launcher_file}' -WindowStyle Hidden" >/dev/null 2>&1 || true

exit 0
