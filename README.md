# jobber

Generate a tailored resume and cover letter from a job description and a folder of your past materials.

`jobber` reads a JD (URL or file), indexes a folder of your past resumes, cover letters, and JDs, maps job requirements to your actual evidence, and drafts a cover letter + resume + a mapping report showing overlap and gaps. Runs from the terminal or from inside Claude Code.

## Why

Cover letters and resumes for every new role are bespoke. The work is the same every time: parse the JD, find the right base resume, map keywords, draft, flag stretches, render PDFs. `jobber` automates the orchestration so you stop redoing it from scratch.

## Install

```bash
pip install -e .                       # from source
jobber init                            # one-time: creates ~/.jobber/ and prompts for your library folder
```

## Quickstart

```bash
jobber apply https://job-boards.greenhouse.io/.../jobs/12345
jobber apply path/to/jd.txt --context "lean on FDA work, ex-Roche hiring manager"
```

Outputs land in `~/.jobber/applications/{company}_{role}_{date}/`:

- `mapping_report.md` / `.pdf` — requirements ↔ evidence with fit ratings and honest gap flagging
- `cover_letter.md` / `.pdf` — drafted in your voice with JD vocabulary where evidence supports
- `resume.md` / `.pdf` — bullets pulled from your library, tailored tagline and summary

## How it works

```
JD ──┐
     ├──► extract requirements (R1..Rn, Q1..Qn, P1..Pn)
     │                                                  ├──► map ──► report + drafts ──► PDFs
your library ──► index evidence (roles, bullets, pubs) ─┘
```

Your "library" is a folder of past resumes, cover letters, JDs, and notes. `jobber` reads it once, extracts evidence with an LLM, caches the index, and re-indexes when files change. **No hand-curated YAML required.**

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
