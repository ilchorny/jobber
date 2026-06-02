# jobber

Generate a tailored resume and cover letter from a job description and a folder of your past materials.

`jobber` reads a JD (URL or file), maps its requirements against a structured database of your achievements, drafts a cover letter + resume + a mapping report, and runs an independent reviewer over the result to catch hallucinations and attribution slips. Runs from the terminal or from inside Claude Code.

## Why

Cover letters and resumes for every new role are bespoke. The work is the same every time: parse the JD, find the right base resume, map keywords, draft, flag stretches, render PDFs. `jobber` automates the orchestration so you stop redoing it from scratch, and gives every application a feedback loop that updates your achievements database for the next round.

## Install

```bash
pip install -e .
jobber init --library /path/to/folder-of-past-materials
jobber extract                         # bootstrap ~/.jobber/achievements.json and ~/.jobber/tone.json from your library
```

## Quickstart

```bash
jobber apply https://job-boards.greenhouse.io/.../jobs/12345
jobber apply path/to/jd.txt --context "lean on FDA work, ex-Roche hiring manager"
jobber review <app-id>                 # auditor pass: flags hallucinations and attribution slips
# (edit cover_letter.md / resume.md by hand)
jobber render <app-id>                 # regenerate PDFs after edits
jobber finalize <app-id>               # copy polished drafts back into library/
```

Outputs land in `~/.jobber/applications/{company}_{role}_{date}/`:

- `mapping_report.md` / `.pdf` — requirements ↔ evidence with fit ratings and honest gap flagging
- `cover_letter.md` / `.pdf` — drafted in your voice with JD vocabulary where evidence supports
- `resume.md` / `.pdf` — bullets pulled from your achievements DB, tailored tagline and summary
- `review.md` / `.pdf` — independent reviewer report (after `jobber review`)

## How it works

```
JD ──► extract requirements (R1..Rn, Q1..Qn, P1..Pn) ──┐
                                                       ├──► map ──► report + drafts ──► PDFs
achievements DB (authoritative facts) ─────────────────┤                  │
tone profile (authoritative voice) ────────────────────┘                  ▼
                                                                       reviewer
                                                                          │
                                                                          ▼
                                                               you edit, then finalize
                                                                          │
                                                                          ▼
                                                  polished drafts → library → next extract
```

Three pipeline stores under `~/.jobber/`, all gitignored, each with a distinct role (the user-edited `profile.yaml` is separate config, not a feedback-loop output):

- **`~/.jobber/library/`**: the raw corpus. Past resumes, cover letters, JDs you've applied to, notes. You add files here whenever you have new material. This is the upstream input to `jobber extract`. It is **never** loaded into a drafting prompt directly — it is compressed into the two structured outputs below.
- **`~/.jobber/achievements.json`**: the structured database produced by `jobber extract` from the library. Every bullet, publication, patent, and credential, each with a stable `attribution` flag (`personally_built`, `directed_team_reviewed`, `led_org`, `co_led`, `co_author`, `contributed`, `partnered_external`). This is the authoritative source for every factual claim in a draft.
- **`~/.jobber/tone.json`**: the tone profile, also produced by `jobber extract` from past cover letters. Captures openers, closers, section pivots, recurring phrases, sentence rhythm, vocabulary, and a "do-not-use" list. This is the authoritative voice guidance for the drafter. Without it, drafts drift toward a generic professional register.

Splitting voice from facts keeps the drafting prompt compact (a 30KB library doesn't get re-sent on every `jobber apply`) and lets you hand-edit `tone.json` to correct over- or under-reaches.

`jobber extract` updates both stores by default. Pass `--no-update-tone` to refresh only the achievements DB.

Any factual claim in a generated cover letter or resume must trace back to an achievement in the DB, not to a raw library file. `jobber review` enforces this by auditing the drafts against the DB.

The reviewer is a separate LLM pass that audits the drafted documents against the DB and the JD. It flags hallucinations (claims with no DB backing), attribution slips (the draft says "I built" but the DB says "directed_team_reviewed"), inaccurate comparisons, and citation errors. Treat its findings as a checklist before you send.

`jobber finalize <app-id>` copies the user-edited cover letter, resume, and JD into the library folder under stable filenames, closing the loop so the next extract sees them.

## Use from Claude Code

```bash
jobber claude-install
```

That installs a thin skill wrapper to `~/.claude/skills/jobber/` and allowlists `jobber` in your Claude Code permissions. After that, every jobber command works from inside a Claude Code session, either as a slash invocation or just by asking Claude in natural language. Claude shells out via Bash, reads the resulting files, and helps you iterate.

### Slash-invocation form

```
/jobber apply <JD URL or path>
/jobber apply <JD URL> --context "lean on FDA work, ex-Roche hiring manager"
/jobber review <app-id>
/jobber render <app-id>
/jobber finalize <app-id>
/jobber finalize <app-id> --refresh-db                       # also refreshes achievements DB and tone profile
/jobber finalize <app-id> --refresh-db --no-update-tone      # refresh achievements DB only
/jobber map <app-id>
/jobber draft <app-id>
/jobber extract               # rebuild achievements DB and refresh tone profile
/jobber extract --overwrite
/jobber extract --no-update-tone   # rebuild achievements DB only; keep tone.json untouched
```

`<app-id>` is the directory name under `~/.jobber/applications/`, e.g. `acme_staff_engineer_2026-05-27`.

### Natural-language form

You can also just talk to Claude. The skill wrapper teaches it which command maps to what:

> "Apply to this JD: https://job-boards.greenhouse.io/.../jobs/12345 and lean on the FDA work."

> "Audit the cover letter for that Illumina application."

> "I edited the resume; re-render the PDFs and push it back to my library."

> "Refresh my achievements DB."

Claude picks up the application id from context, surfaces the mapping report's key findings, and offers next steps (edit the mapping, provide more context, iterate on drafts, finalize).

### Typical Claude Code workflow

1. Paste a JD URL into the session.
2. Claude runs `jobber apply` and summarizes the mapping report (fit counts, honest gaps).
3. You ask Claude to run the reviewer; it surfaces any hallucinations or attribution slips.
4. You edit `cover_letter.md` and `resume.md` in the editor of your choice.
5. Claude re-renders PDFs and runs `jobber finalize` so the next extract sees your final language.

## Privacy

`jobber` is built around a hard line between the code (this repo) and your data:

- **In this repo:** code, generic prompt templates, tests, an anonymized sample profile (fictional "Alex Park").
- **On your machine only:** everything in `~/.jobber/` — your profile, library, drafts, applications.

Nothing in `~/.jobber/` is ever read by the repo's build, tests, or examples. A pre-commit hook scans staged files against a local blocklist (`.personal-data-blocklist`, gitignored) so you can refuse commits that contain your name, email, phone, etc.

If you keep a richer profile on your machine (e.g., notes synced from Claude Code's memory system), you can opt into seeding it with:

```bash
jobber init --seed-from-claude-memory
```

This reads `~/.claude/projects/*/memory/*.md` and copies the relevant facts (voice rules, attribution overrides) into your local `~/.jobber/profile.yaml`. It writes nowhere else.

## Status

Alpha. Phase 1 ships the CLI + Claude Code skill wrapper end-to-end. Interactive mapping editor, feedback/learning loop, and web UI are on the roadmap.

## License

MIT.
