---
name: jobber
description: Generate, review, and finalize tailored resumes and cover letters from a JD using the user's local achievements DB and library. Invokes the `jobber` CLI via Bash. Use when the user provides a JD (URL, file, or pasted text) and asks for an application, cover letter, resume, audit, or "apply to this job".
---

# jobber skill

You orchestrate the `jobber` CLI for the user. The CLI does the heavy lifting (JD parsing, evidence indexing, mapping, drafting, auditing, PDF rendering). Your job is to invoke the right command at the right moment and help the user iterate.

## When to invoke

- User pastes or links a JD and asks for an application / cover letter / resume.
- User explicitly types `/jobber` or asks to "run jobber".
- User asks to audit, review, edit, render, or finalize an existing application.
- User asks to refresh their achievements DB.

## Commands and when to use them

| Command | When to use |
|---|---|
| `jobber apply "<JD URL or path>" [--context "<extra>"]` | Full pipeline. First step for every new application. |
| `jobber review <app-id>` | After `apply`. Audits the drafts for hallucinations, attribution slips, inaccurate comparisons, citation problems. |
| `jobber render <app-id>` | After the user hand-edits `cover_letter.md` or `resume.md`. Regenerates PDFs from the markdown. |
| `jobber finalize <app-id> [--refresh-db] [--no-update-tone]` | When the user signals the application is ready to send. Copies the polished drafts back into the library folder so the next extract sees them. `--refresh-db` also refreshes the achievements DB and the tone profile inline (pass `--no-update-tone` to skip the tone refresh, e.g. if the user has hand-edited `~/.jobber/tone.json`). |
| `jobber map <app-id>` | If the user wants to re-rank the evidence mapping before re-drafting. Opens mapping.json in $EDITOR. |
| `jobber draft <app-id>` | Re-runs drafting using the current mapping. Use after `jobber map` edits, or after profile/DB changes. |
| `jobber extract [--overwrite] [--no-update-tone]` | Bootstraps or refreshes the achievements DB from the library folder. Run once at setup, or after adding new files to the library. By default also re-extracts the tone profile from `library/cover_letters/`; pass `--no-update-tone` to skip that (useful when you've hand-edited `~/.jobber/tone.json` and don't want it overwritten). |
| `jobber init [--library <path>] [--seed-from-claude-memory]` | First-time setup. Creates `~/.jobber/`, optionally links a library folder, optionally seeds voice/attribution rules from `~/.claude` memory. |

## Primary flow

1. Identify the JD. It may be a URL, a path to a local file, or pasted text.
2. Collect any extra context the user offered (target thesis, recruiter intel, "lean on X", "this team is led by ex-Y").
3. Run via Bash:

   ```bash
   jobber apply "<JD URL or path>" [--context "<extra context>"]
   ```

   If the JD is pasted text, save it to a temp file first and pass the path.
4. After it completes, read `~/.jobber/applications/{app_id}/mapping_report.md` and surface the key findings to the user: fit summary (strong/moderate/weak/none counts), honest gaps, the thesis candidates jobber considered.
5. Offer to run the reviewer (`jobber review {app_id}`). Strongly recommend it before the user edits or sends anything.
6. After the user edits the drafts by hand, run `jobber render {app_id}` to regenerate the PDFs, then `jobber finalize {app_id}` to push polished material back into the library.

## Iteration helpers

- To re-rank evidence before re-drafting: `jobber map {app_id}` opens mapping.json in the user's editor.
- After mapping edits: `jobber draft {app_id}` re-runs drafting with the new mapping.
- After hand-editing `cover_letter.md` or `resume.md`: `jobber render {app_id}` regenerates the PDFs.

## Things to NOT do

- Do not invent evidence. The achievements DB is the authoritative source. If a JD requirement has no matching DB entry, the mapping report will already flag it as an honest gap; surface that to the user rather than papering over it.
- Do not edit `~/.jobber/achievements.json` directly without asking; that file is hand-curated by the user and small drift accumulates.
- Do not push generated documents anywhere external. Outputs stay under `~/.jobber/applications/`.
- Do not run `jobber init --seed-from-claude-memory` without the user explicitly asking. It is opt-in for a reason: it reads `~/.claude/projects/*/memory/*.md` and writes derived facts into the user's local profile.

## First-time setup hints

If `jobber apply` fails with "achievements DB is empty" or "library index is empty", walk the user through:

- `jobber init --library <path-to-their-library-folder>` to register a library.
- `jobber extract` to bootstrap the achievements DB.

If it fails with "ANTHROPIC_API_KEY is not set" AND `claude` is not on PATH, the user needs one of: install Claude Code or export `ANTHROPIC_API_KEY`. When invoked from inside Claude Code itself, the `claude` CLI is already on PATH and jobber uses it as the LLM backend automatically.

## Google Drive libraries

**The CLI is filesystem-only by design**: the standalone `jobber` subprocess has no MCP access, so it cannot fetch from Google Drive. The MCP belongs to your Claude Code session, not to the CLI. *You* (the in-session assistant) handle the Drive sync; the CLI sees only local paths.

### When to intercept

Intercept whenever the user gives you a Google Drive folder URL or folder ID in the context of `jobber init --library` (or "point jobber at my Drive folder"). Recognizable signals:

- A URL containing `drive.google.com` or `docs.google.com`.
- A bare folder ID like `1MutdFlSIjp_26ZBNjBjsphQLZjzpgNu8` (alphanumeric ID, typically 25–44 chars, no slashes, given in a context where a folder is meant).
- The user saying "my Google Drive folder" without giving a local path.

If the Google Drive MCP is NOT available in this session (no `mcp__claude_ai_Google_Drive__*` tools), tell the user you can't sync and offer the manual `gdrive` / `rclone` / Drive UI download path.

### The intercept procedure

1. **Pick the local destination.** Default `~/jobber-library/`. If the directory already exists and contains files the user may want to keep, ask before overwriting. Create the standard subfolders: `resumes/`, `cover_letters/`, `jds/`, `notes/`.
2. **List the Drive folder** with `mcp__claude_ai_Google_Drive__search_files` and a query like `parentId = '<folder-id>'`. Page through results if the folder is large.
3. **Classify each file before downloading.** A simple heuristic:
   - filename matches `*resume*` / `*cv*` / `*CV*` → `resumes/`
   - filename matches `*cover*letter*` → `cover_letters/`
   - filename contains a JD-shaped marker (`*jd*`, `*job_description*`, `*JD*`) → `jds/`
   - interview prep, notes, fact cards → `notes/`
   - obviously non-job-search material (taxes, photos, financial reports, audio/video, signed contracts that aren't employment-related) → skip
4. **Show the planned file list to the user before downloading.** They should confirm the classification and skip list. For large folders, summarize counts per bucket and offer to download a subset.
5. **Download** the approved set via `mcp__claude_ai_Google_Drive__download_file_content` (binary) or `mcp__claude_ai_Google_Drive__read_file_content` (for native Google Docs/Sheets, which need a different code path). Write each file into the correct local subfolder, preserving the original filename.
6. **Then call the CLI** with the local path:

   ```bash
   jobber init --library ~/jobber-library
   jobber extract
   ```

7. **Surface what landed**: count and names of files per bucket, anything skipped, and the resulting achievements-DB summary from `jobber extract`.

### What to do if the user passes a Drive URL to `jobber init --library` literally

The CLI will reject it with a clear error. Do NOT just relay that error to the user — that's a failure of orchestration. Instead, on seeing the rejection, run the intercept procedure above and re-invoke `jobber init --library <local-path>` for them.

### Ongoing sync

If the user wants the library to stay in sync with Drive over time, that is a manual `jobber sync` they request. There is no automatic poll. After re-syncing, run `jobber extract --overwrite` (or `jobber finalize <app-id> --refresh-db`) to fold the new material into the achievements DB.
