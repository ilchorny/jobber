---
name: jobber
description: Generate a tailored resume and cover letter from a JD using your local library of past materials. Invokes the `jobber` CLI via Bash. Use when the user provides a JD (URL, file, or pasted text) and asks for an application, cover letter, resume, or "apply to this job".
---

# jobber skill

You orchestrate the `jobber` CLI for the user. The CLI does the heavy lifting (JD parsing, library indexing, mapping, drafting, PDF rendering). Your job is to invoke it correctly and help the user iterate.

## When to invoke

- User pastes or links a JD and asks for an application / cover letter / resume.
- User explicitly types `/jobber` or asks to "run jobber".
- User asks to update or re-draft an existing application.

## Primary flow

1. Identify the JD. It may be a URL, a path to a local file, or pasted text.
2. Collect any extra context the user offered (target thesis, recruiter intel, "lean on X", "this team is led by ex-Y").
3. Invoke the CLI via Bash:

   ```bash
   jobber apply "<JD URL or path>" [--context "<extra context>"]
   ```

   If the JD is pasted text, save it to a temp file first and pass the path.
4. After it completes, read `~/.jobber/applications/{app_id}/mapping_report.md` and surface the key findings to the user: fit summary, honest gaps, thesis candidates the system considered.
5. Offer next steps: edit the mapping, provide more context, iterate on the drafts.

## Iteration helpers

- To re-rank evidence before re-drafting: `jobber map {app_id}` opens mapping.json in the user's editor.
- After mapping edits: `jobber draft {app_id}` re-runs the drafting with the new mapping.
- After hand-editing `cover_letter.md` or `resume.md`: `jobber render {app_id}` regenerates the PDFs.

## Things to NOT do

- Do not invent evidence. If a JD requirement has no matching library evidence, the mapping report will already flag it as an honest gap; surface that to the user, do not paper over it.
- Do not write personal data (names, employer history, attributions) into prompts that the user did not put in their library. The CLI handles all of that from `~/.jobber/`.
- Do not push generated documents anywhere external. Outputs stay under `~/.jobber/applications/`.

## First-time setup

If `jobber apply` fails with "library index is empty" or "ANTHROPIC_API_KEY is not set," walk the user through:

- `jobber init --library <path-to-their-library-folder>` to register a library.
- Setting `ANTHROPIC_API_KEY` in their shell.

Do not run `jobber init --seed-from-claude-memory` unless the user explicitly asks. It is opt-in for a reason: it reads Claude Code memory files and writes the extracted facts into `~/.jobber/profile.yaml`.
