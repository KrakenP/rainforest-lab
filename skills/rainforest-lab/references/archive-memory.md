# Archive Memory

Archive memory lets future agents resume research without rediscovering context.

## Update After Every Cycle

Update:

- Forest state.
- Seed bank.
- Weather log.
- Cycle report.
- Golden Leaf pool.
- Sick Leaf warnings.
- Open questions.
- Next-cycle task candidates.

## Memory Principles

- Keep decisions inspectable.
- Preserve reasons, not only labels.
- Separate evidence from speculation.
- Keep mock or stub results clearly marked.
- Record why seeds were held, rejected, or quarantined.
- Do not delete failures that explain future risks.

## Cycle Report Sections

```markdown
# Cycle Report

## Forest Snapshot

## Weather Decisions

## Sown Seeds

## Completed Tasks

## Result Classifications

## New Seeds Captured

## Archive Updates

## Next Cycle
```

## Resume Prompt

End reports with a short prompt a future agent can use:

```text
Resume Rainforest from this archive. First inspect the latest forest state, seed bank, weather log, and cycle report. Continue from the next-cycle tasks unless the user changes the goal.
```
