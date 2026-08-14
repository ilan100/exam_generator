# Exam Generator — Claude Code Session Handoff

Use this procedure whenever development resumes in a new Claude Code session.

## Resume Prompt
Copy/paste the following into the new Claude Code session:

---

We are continuing development of the Exam Generator project.

Before doing any implementation:

1. Read `docs/MASTER_PROJECT_BRIEF.md` completely.
2. Read `docs/ARCHITECTURE.md` completely.
3. Read `docs/PROJECT_STATUS.md` completely.
4. Inspect the current repository structure.
5. Read the relevant existing code and tests needed to understand the current implementation state.
6. Do not modify any files yet.
7. Do not start the next Work Package yet.
8. Do not rely on memory from previous Claude sessions. The repository and project documents are the source of truth.

Report back with:
- your understanding of the project's purpose and non-negotiable source/grounding rules;
- the last completed Work Package;
- the current implementation state;
- important established interfaces/configuration contracts;
- current test status;
- known issues or deferred work;
- the next planned Work Package number/title according to `PROJECT_STATUS.md`.

If repository state conflicts with the documentation, report the discrepancy explicitly rather than silently choosing one.

Wait for the next Work Package instruction after reporting. Do not implement anything until it is supplied.

---

## Normal Work Package Rules
Once a WP is supplied:
- Read it fully before editing.
- Implement only that WP.
- Do not implement future WPs early.
- Do not redesign architecture silently.
- Stop and report material ambiguity/conflict.
- Run required tests and existing relevant regression tests.
- Update `docs/PROJECT_STATUS.md` only after successful completion.
- Update `docs/ARCHITECTURE.md` only if the WP establishes/changes a durable architecture/interface decision.
- Finish with a factual completion report: files changed, behavior implemented, tests/commands/results, status-document changes, known issues, and deferred items.
- Create WP completion report in a markdown file.

## End-of-Session Rule
Before intentionally ending a development session after completed work, confirm that `docs/PROJECT_STATUS.md` accurately reflects the repository's current state. A future Claude session must be able to resume from the repository without conversational memory.
