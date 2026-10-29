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

## Regression and discovery tracks

Use `--candidate-only --install-skill` to run the current core with a local copy of the complete skill.
Use `--suite evals/heldout-grounding.json` for unfamiliar rewrite and local-evidence prompts.
Use `--discovery-only --suite evals/discovery-grounding.json` to omit project core injection and test natural skill selection.
Existing global instructions still apply. Record which skill path the model reads; a global copy does not prove local discovery.
The discovery case requests a video plan only. It does not validate rendering, audio, or interactive HTML.

For Claude Code, compare runs with and without `--disable-style` using the same model and prompts.
The flag disables only the explanatory-output-style plugin for that process. Check the startup trace before attributing a difference.
Do not count unavailable models, timeouts, or missing tool results as writing failures.
Keep interrupted runs, use a new directory for a retry, and report both outcomes.

Keep Context7 optional. If no connector is available, evaluate official-source retrieval and mark Context7 untested.
Full format validation needs a separate writable artifact workspace and render/browser tools.
Do not treat the read-only planning suite as end-to-end media validation.

Use `--route-skill` to append the production artifact router to the project instructions.
Combine it with `--discovery-only` to test routed loading without injecting the shared core.
The user prompt remains unchanged. The router explicitly identifies the local entrypoint.
Do not report routed loading as unassisted native discovery.

Run `python3 scripts/check_writing.py /path/to/answer.md` to flag long prose for review.
The checker skips code, quotations, headings, and tables. Review those exclusions and all procedure rules manually.
It does not grade factual accuracy, passive voice, scope, or meaning.

The runner freezes the installed skill tree and records file hashes before starting model calls.
Use `--candidate-default /path/to/core.md` for a shared candidate experiment without changing the checkout during a run.
The frozen skill receives that same core, including in routed-loading tests.
Record stopped exploratory runs separately. Do not merge their partial results into a completed final matrix.

## Empty responses and infrastructure errors

The runner records `response_missing` when a command exits successfully without an answer.
It preserves that first attempt and continues independent cases without retrying.
The overall command still exits with status 2. A missing response is never a pass.
An explicit provider error, nonzero exit, or timeout stops the run; remaining cases stay unrun.
OpenCode session export uses the same executable as the trial.
Keep model changes and retries in separate, clearly identified experiments.
