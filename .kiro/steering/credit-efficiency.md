---
inclusion: always
---
# Credit and token efficiency

These rules keep every DataObs agent cheap and fast. They never override
`safety-and-evidence.md`; correctness and evidence integrity always win.

## Read less, read once
- Prefer `grep`/`file_search`/`read_code` with a `selector` over full-file reads.
  Only read a whole file when you will edit it or must understand its full flow.
- Never re-read a file already in context this session. Trust prior reads unless an
  edit changed the file.
- When exploring an unfamiliar area, delegate one scoped investigation to a
  sub-agent (context-gatherer) instead of many small reads in the main thread.
  Treat its findings as your reads.
- Read targeted line ranges, not entire large files. Use `offset`/`limit`.

## Edit precisely
- Use `str_replace` with the smallest unique anchor, not full-file rewrites.
- Make all independent tool calls in one batch (parallel), not one at a time.
- Do not run a command and then a second command that only confirms the first
  succeeded. Trust exit codes.

## Verify proportionally
- Run the smallest test set that proves the change first. Only widen scope when
  that passes or when release gates require it.
- Do not re-run lint/format/tests that already passed unless the code changed since.
- Prefer one combined `ruff && black --check && pytest <targeted>` over three
  separate turns.

## Stay scoped
- Work only on the owned task. Do not refactor, reformat, or "clean up" unrelated
  code — it burns credits and risks other teams' work.
- Stop when the task's exit criteria are met. Do not gold-plate.
- If blocked, state the blocker and stop rather than exploring speculatively.

## Communicate compactly
- Keep chat replies short. Put detail in the PR/commit, not the conversation.
- One concise end-of-task summary, not running narration.

## Model and effort
- Use low effort for mechanical tasks (version bumps, formatting, doc edits,
  single-file fixes). Reserve high effort for design, multi-file features, and
  release certification reasoning.
