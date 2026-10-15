# Compare shared writing defaults

This experiment compares a previous default with the current `CORE.md` on five unfamiliar prompts.
It tests meaning preservation, runbook scope, local evidence, version mismatch, and an official documentation lookup.
It is separate from the original 23-case suite. It does not claim to test automatic skill selection.

## Run

Save the previous writing default outside the repository. Use a fresh output directory for each harness.

```sh
python3 scripts/compare_defaults.py --harness opencode \
  --model ollama/kimi-k3:cloud --baseline-default /tmp/previous-default.md \
  --out /tmp/explain-opencode-comparison
```

Use `--harness codex` or `--harness claude-code` with an explicit model identifier for the other harnesses.
Use `--executable` to select an existing CLI installation when PATH resolves a different version.
Each prompt runs three times per condition. The order alternates between repetitions.
The runner invokes real models and may use the user's provider quota. It never changes saved model preferences or global instruction files.
It stops on an infrastructure failure and retains partial results. Use a new output folder for any retry.

Each trial receives the same unmodified task prompt, with no skill invocation.
The treatment enters through the harness's project instruction file. Review criteria stay outside the trial workspace.
The baseline is the supplied previous default; the candidate is a frozen copy of `CORE.md`.
Both conditions retain existing global instructions and installed skills. This is a paired local-configuration experiment, not a clean-room causal test.
Inspect startup hooks for conflicting instructions. The same model can receive different instructions through plugins or output-style settings.

Codex uses its read-only sandbox. Claude exposes only read, search, fetch, and skill tools.
OpenCode V2 receives agent-level permission rules that deny other actions, including editing and shell commands.
These mechanisms are not identical. Inspect attempted mutations as well as actual file changes, and report policy differences.
The runner sets both the process directory and `PWD`; OpenCode V2 otherwise can retain the parent's location.

## Review

Review complete answers and tool events against the frozen criteria in `suite.json`.
Assign pass, fail, blocked, or pending for each criterion in `execution.json`, with concrete evidence.
A trial passes only when every criterion passes. Report missing results separately from failures.
Do not use sentence counts to grade meaning or factual accuracy.

Keep these dimensions separate:

- Instruction delivery: input hashes, actual working directory, project instruction injection, and any observed reads.
- Skill discovery: explicit load events, independent of answer quality.
- Model identity: requested identifier and resolved session metadata, when exposed.
- Research: tool use, relevant source/version, and supported claims.
- Writing: sentence limits, one action per instruction, and readable wording.
- Meaning: capability versus behavior, plans versus commitments, completed results versus present claims.
- Scope: attempted edits, extra artifacts, and unsolicited writing audits.

A correct answer with a citation does not prove a lookup occurred. Mark missing lookup evidence separately.
A documentation result for another version does not establish the installed version's behavior.
The synthetic PacketShelf fixture tests this distinction without relying on a real vendor.

For the Python case, use [Python 3.12 sqlite3 documentation](https://docs.python.org/3.12/library/sqlite3.html).
Check the default `LEGACY_TRANSACTION_CONTROL` and the documented effect of `commit()` when `autocommit=True`.
Do not change the rubric after seeing the candidate's answers. Apply any discovered scoring correction to both conditions.

## Limits and follow-up

These are small regression trials, not general model rankings or formal STE certification.
The research case tests available documentation tools, not a mandatory Context7 integration.
Repeat failures on fresh held-out prompts before adding a model adapter.
Run native discovery and fresh HTML/video cases separately before claiming end-to-end portability.
Raw traces can include machine or account details; keep them local and publish only reviewed summaries.
