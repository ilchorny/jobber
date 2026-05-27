# jobber

Generate a tailored resume and cover letter from a job description and a folder of your past materials.

`jobber` reads a JD (URL or file), maps its requirements against a structured database of your achievements, drafts a cover letter + resume + a mapping report, and runs an independent reviewer over the result to catch hallucinations and attribution slips. Runs from the terminal or from inside Claude Code.

## Why

Cover letters and resumes for every new role are bespoke. The work is the same every time: parse the JD, find the right base resume, map keywords, draft, flag stretches, render PDFs. `jobber` automates the orchestration so you stop redoing it from scratch, and gives every application a feedback loop that updates your achievements database for the next round.

## Install

```bash
pip install -e .
jobber init --library /path/to/folder-of-past-materials
jobber extract                         # bootstrap ~/.jobber/achievements.json from your library
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
achievements DB (authoritative) ───────────────────────┘                  │
library (voice samples)                                                   ▼
                                                                       reviewer
                                                                          │
                                                                          ▼
                                                               you edit, then finalize
                                                                          │
                                                                          ▼
                                                  polished drafts → library → next extract
```

Two layers of evidence on your machine, both gitignored:

- **`~/.jobber/achievements.json`**: structured database of every bullet, publication, patent, and credential, each with a stable `attribution` flag (`personally_built`, `directed_team_reviewed`, `led_org`, `co_led`, `co_author`, `contributed`, `partnered_external`). This is the authoritative source for every draft.
- **`~/.jobber/library/`**: supplementary text and voice samples (past resumes, cover letters, JDs, notes). Used for voice context and as input to `jobber extract`; never a free source of new facts for the drafter.

The reviewer is a separate LLM pass that audits the drafted documents against the DB and the JD. It flags hallucinations (claims with no DB backing), attribution slips (the draft says "I built" but the DB says "directed_team_reviewed"), inaccurate comparisons, and citation errors. Treat its findings as a checklist before you send.

`jobber finalize <app-id>` copies the user-edited cover letter, resume, and JD into the library folder under stable filenames, closing the loop so the next extract sees them.

## Use from Claude Code

```bash
jobber claude-install
```

That installs a thin skill wrapper to `~/.claude/skills/jobber/` and allowlists `jobber` in your Claude Code permissions. After that, you can type:

```
/jobber apply <JD URL>
```

or just paste a JD into a Claude Code conversation and ask for an application. Claude invokes the CLI, surfaces the mapping report, and helps you iterate.

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
