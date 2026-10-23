# Development Process

- Track work as GitHub issues when the project backlog uses them.
- Commit regularly, after the relevant checks pass.

Labels

- Use `mvp` for work required by the currently agreed MVP and `post-mvp` for
  work explicitly deferred beyond it, if those labels are used by the
  repository.
- Do not assume an issue has a label or acceptance criteria that have not
  actually been recorded.

Background

- Read `AGENTS.md`, `README.md` before grooming or
  implementing a task.
- Treat implementation details in the code and its tests as authoritative
  when they differ from a handover or planned architecture. Report material
  discrepancies rather than silently inventing behavior.
- Keep agreed project decisions with the project documentation; do not
  introduce a new decision by treating an old plan as current.

Roles

- PM - clarifies the task and acceptance criteria before implementation.
- Engineer - implements one well-scoped task and runs the relevant checks.
- QA - verifies the result against the acceptance criteria and reports
  failures; QA does not make unrequested code changes.

Orchestrator

The main session coordinates task selection, dependencies, worktrees, and
integration. It may delegate grooming, implementation, and verification, but
delegation does not replace checking that the requested outcome is met.

Working in parallel

Work can proceed in waves when tasks are independent.

- Run agents in parallel only when their tasks do not depend on one another
  and their changes are unlikely to conflict.
- Give each concurrent implementation task its own worktree and branch.
- Keep changes isolated from the main checkout until integration.

A task may enter a wave only when:

- Its prerequisites are complete.
- It does not conflict with another task's ownership of shared files or
  database migrations.
- Its acceptance criteria and expected files are understood.

Do not parallelize tasks merely to fill an agent limit.

Worktrees

Use one worktree and branch per concurrent task. Set up each worktree using
the repository's documented Python and environment setup:

- Run `uv sync` from `backend/` when that directory and its `pyproject.toml`
  are present.
- Configure a worktree-specific `DATABASE_URL` in its `.env`. Use a separate
  SQLite database file for local SQLite work, or a distinct PostgreSQL
  database for containerized work.
- Never let concurrent worktrees or test runs write to the same database.
- Keep secrets out of Git; use `.env` and the repository's environment
  template.

Before an agent starts, confirm its environment selects the intended
database. Follow the configured `DATABASE_URL`; do not assume framework-
specific settings modules, management commands, or database names from
another project.

The project uses SQLAlchemy with SQLite for local/self-hosted use and
PostgreSQL for containerized deployment. Use SQLAlchemy for database access.
Database schema changes require confirmation and must be made through Alembic
migration scripts in `/migrations`; do not create or alter tables at runtime.

Run one database-backed test suite at a time in each worktree unless the test
configuration explicitly isolates its databases per process. If a run fails
unexpectedly, confirm no other run is using the same database before
repeating it. Wait for checks to finish and report timeouts or failures
explicitly.

Do not terminate processes that you did not start. Stop a background command
using the specific job or process handle provided by the tool that started
it.

Destructive commands and cleanup

- Do not remove worktrees, branches, databases, or user files without
  authorization.
- Avoid destructive cleanup as part of routine integration. If cleanup is
  necessary, explain what will be removed and why, then obtain approval.
- Do not discard changes that you did not make. Before finishing, inspect
  `git status` and the diff for the files you changed.
- Put temporary files outside the repository unless the task requires them
  to be part of the change.

Integration

Integrate branches one at a time, in dependency order:

1. Rebase the branch onto the current main branch.
2. Run the relevant tests and lint checks again after rebasing.
3. Merge only when checks pass and the acceptance criteria are met.
4. Push the integrated changes when the repository workflow calls for it.
5. Close the issue only after its work is integrated and verified.
6. Rebase remaining branches as needed, then rerun checks affected by the
   integration.

Use the project's Python commands rather than another framework's tooling:

```bash
cd backend
uv run pytest -v
uv run ruff check . ../migrations
uv run ruff format --check . ../migrations
```

When the React/Vite frontend is present, also run its configured checks. Do
not assume frontend files, commands, or functionality exist until they are
present in the repository.

If integration exposes a conflict or regression, resolve it in the
responsible branch and rerun the relevant checks. Do not merge a branch whose
rebased result has not been verified.

Lifecycle

1. Select a task whose prerequisites are complete.
2. Clarify its scope and acceptance criteria before implementation.
3. Set up an isolated worktree for concurrent work.
4. Have the engineer implement the task and run the relevant checks.
5. Have QA verify the implementation against the acceptance criteria.
6. On failure, send the findings back to the engineer; keep unrelated tasks
   moving.
7. On success, integrate and verify the branch, then close the task if
   applicable.
8. Continue with the next ready task.

Rules

- One task per worktree and one engineer per worktree at a time.
- Do not skip task clarification when acceptance criteria are unclear.
- The engineer does not close the issue; QA reports results and does not fix
  code.
- Do not commit until the relevant tests and checks pass.
- An agent writes only in its assigned worktree.
- Only the orchestrator integrates branches and closes issues.
- Ask before introducing third-party dependencies or changing the database
  schema.
