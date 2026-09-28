---
name: continue-sprint
description: Continue a project from durable evidence rather than a stale chat.
---
# Continue Sprint

## Trigger
Use when the task specifically calls for this activity. Do not load every skill for every role.

## Inputs
PROJECT.md, current status, last run and outstanding issues.

## Procedure
Reproduce the most important blocker, select one acceptance criterion, implement within scope, verify and update status. Check rules and dependency changes before external effects.

## Deliverable and completion test
One verified improvement and a clean next-session handoff.

## Failure and safety boundaries
Do not expand into a general agent platform or treat old approvals as unlimited authority.

## Integration status
This is a reviewed instruction file, not an executable tool. v0.2 explicitly loads selected role-scoped skill files through predictkit/skills.py and records their hashes. This is local request assembly, not universal native SDK skill discovery. Verify a real request before claiming live use. It cannot grant access, execute code or replace deterministic validation by itself.
