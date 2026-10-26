# Project Team

The project uses three delivery roles, coordinated by an orchestrator. These
roles describe responsibilities in the project workflow; documenting them
does not by itself establish that a role was invoked for a particular task.

| Role | Responsibility | Does not |
| --- | --- | --- |
| Product Manager (PM) | Clarifies scope, constraints, and verifiable acceptance criteria before implementation. | Write implementation code. |
| Software Engineer | Implements one agreed task, adds or updates relevant tests, and runs applicable checks. | Change acceptance criteria or close a task unless the workflow explicitly assigns that responsibility. |
| QA Engineer | Verifies the implementation against acceptance criteria, runs relevant checks, and reports failures. | Make unrequested implementation changes. |
| Orchestrator | Selects and coordinates work, manages dependencies and any delegation, integrates completed changes, and confirms the requested outcome. | Treat delegation as a substitute for integration and verification. |

## Collaboration Workflow

1. The PM clarifies the task and writes objectively verifiable acceptance
   criteria. Track project work in the linked GitHub issue when applicable.
2. The orchestrator assigns a well-scoped task to the Software Engineer and
   provides its acceptance criteria and relevant project context.
3. The Software Engineer implements the task and reports the exact tests and
   checks run. Database schema changes require prior confirmation and must use
   Alembic migrations under `/migrations`.
4. The QA Engineer independently checks the acceptance criteria against the
   implementation and reports pass/fail evidence. Failed criteria return to
   engineering for correction.
5. The orchestrator integrates only after required checks pass, then updates
   the linked task according to the repository workflow.

Work may be parallelized only when tasks are independent, their ownership is
clear, and changes are isolated. See the [development process](./process.md)
for the worktree, testing, and integration rules.

## Role Guides

- [Product Manager](./team/pm.md)
- [Software Engineer](./team/software-engineer.md)
- [QA Engineer](./team/qa-engineer.md)
