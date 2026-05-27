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
| `jobber finalize <app-id> [--refresh-db]` | When the user signals the application is ready to send. Copies the polished drafts back into the library folder so the next extract sees them. `--refresh-db` also re-runs extract inline. |
| `jobber map <app-id>` | If the user wants to re-rank the evidence mapping before re-drafting. Opens mapping.json in $EDITOR. |
| `jobber draft <app-id>` | Re-runs drafting using the current mapping. Use after `jobber map` edits, or after profile/DB changes. |
| `jobber extract [--overwrite]` | Bootstraps or refreshes the achievements DB from the library folder. Run once at setup, or after adding new files to the library. |
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

The `jobber init --library` flag wants a local filesystem path. If the user's past materials live in a Google Drive folder and they ask you to "use" or "point jobber at" that folder, do this:

1. Pick or create a local destination, e.g. `~/jobber-library/`. Make the subfolders `resumes/`, `cover_letters/`, `jds/`, `notes/` if they don't exist.
2. If the Google Drive MCP is available in the current session (look for tools like `mcp__claude_ai_Google_Drive__search_files`, `mcp__claude_ai_Google_Drive__read_file_content`, `mcp__claude_ai_Google_Drive__download_file_content`), use it to:
   - List the folder contents (`search_files` with `parentId = '<folder-id>'`).
   - Download each relevant file (resumes, cover letters, JDs, notes) into the appropriate local subfolder. Skip files that are clearly not job-search material (tax docs, photos, unrelated PDFs).
   - Confirm the file count with the user before proceeding.
3. Then call:

   ```bash
   jobber init --library ~/jobber-library
   jobber extract
   ```

Do NOT pass a Drive URL or Drive folder ID directly to `jobber init --library`. The CLI will reject it because the standalone jobber process has no Drive access. The MCP belongs to your session, not to the CLI subprocess.

If the user wants the library to stay in sync with Drive over time, surface that as a manual step for now: re-run the MCP-driven sync, then `jobber finalize <app-id> --refresh-db` or `jobber extract --overwrite` to refresh the achievements DB.
