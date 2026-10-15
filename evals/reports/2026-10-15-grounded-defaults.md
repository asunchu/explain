# Paired default evaluation: October 15, 2026

## Result

The candidate improved these sampled results, but failures remain. Do not treat this as a universal compatibility claim.

| Harness and model | CLI | Previous default | Shared core |
| --- | --- | ---: | ---: |
| Codex / gpt-6.1-sol | 0.162.1 | 15/15 | 15/15 |
| Claude Code / claude-opus-5-5 | 2.1.296 | 9/15 | 14/15 |
| OpenCode / ollama/kimi-k3:cloud | 2.0.28 | 9/15 | 11/15 |

Five unfamiliar prompts ran three times per condition: 90 completed trials.
Prompts did not mention Explain, STE, a skill path, or a skill command.
The project instruction file supplied the old default or the candidate core. Both conditions kept the existing global setup.
The order alternated between repetitions. No model setting or global instruction file changed.

[Per-case judgments](2026-10-15-grounded-defaults.json) include every criterion and the hash of its reviewed answer.
Raw answers, native events, source snapshots, and full session exports remain local.
The primary assistant reviewed every answer and tool trace. There was no independent second reviewer.

## Results by case

Each cell shows previous default → shared core.

| Case | Codex | Claude Code | OpenCode / Kimi K3 |
| --- | --- | --- | --- |
| Preserve capability, plan, and timing | 3 → 3 | 0 → 2 | 0 → 2 |
| Recovery runbook | 3 → 3 | 0 → 3 | 1 → 3 |
| Local code evidence | 3 → 3 | 3 → 3 | 2 → 2 |
| Documentation version gap | 3 → 3 | 3 → 3 | 3 → 2 |
| Official Python documentation | 3 → 3 | 3 → 3 | 3 → 2 |

All 54 research-bearing trials showed relevant source retrieval. No fixture files changed in the 90 trials.
Research access did not guarantee a correct answer. Kimi fetched the right Python page, then added a false Python 3.14 claim.
The [Python 3.14 signature](https://docs.python.org/3.14/library/sqlite3.html#sqlite3.connect) still uses `LEGACY_TRANSACTION_CONTROL`.

## Candidate failures

- Claude added an unsolicited explanation of its rewrite in one meaning trial.
- Kimi added an unsolicited explanation of an omission in one meaning trial.
- Kimi used a 36-word sentence in one local-code explanation.
- Kimi asserted an installed version, then said installation could not be established in the same answer.
- Kimi incorrectly said the autocommit default changed in Python 3.14.

The capability example helped: Kimi preserved capability in all three candidate rewrites, compared with none under the old default.
The shared core also reduced writing-audit notes. It did not remove every extra note or factual error.

Educational comments about code are not automatically writing audits. The rubric penalizes unsolicited explanations of the writing process.
Sentence counts exclude code and protected quotations. Table rows and quoted passages require manual review, not a simple regex verdict.
Passing a sampled rubric does not certify every incidental claim, formal STE compliance, or future behavior.

## Loading and environment findings

1. Claude's startup hook from `explanatory-output-style` requests Insight blocks and permits exceeding typical length constraints.
   This competes with the shared writing rules. The plugin was not disabled for this comparison.
2. The first Claude launch resolved CLI 2.1.236, which rejected the pinned model.
   That failed attempt was preserved and excluded. An existing 2.1.296 executable completed both conditions with the same model.
3. OpenCode loaded the installed Explain skill in one baseline trial, then could not read its external reference files.
   The original test permissions allowed skill loading but denied those external-directory reads.
4. The runner now grants read access to both the installed skill path and its resolved target.
   Separate loading probes verified the canonical path first, then both reference files directly through the symlink path.
   The main comparison was not rerun or relabeled after that permission fix.
5. Codex read the installed Explain entrypoint in 8/30 trials. Claude showed no skill-load calls. OpenCode showed one in 30.
   Those reads concerned the existing installed skill. The candidate treatment was the new shared core in project instructions.
6. All 30 Claude and all 30 OpenCode session records confirmed the selected model and trial directory.
   Codex commands pinned the model; its JSON events did not provide equivalent resolved-model metadata.
7. Codex also used its existing memory and installed skills in some trials. This experiment retained the user's real setup.

These findings do not isolate model behavior from harness configuration, plugins, permissions, or prior global instructions.
Tool policies differ by harness, though both conditions within each harness used the same policy.
Context7 itself was not exercised. The documentation cases used native fetch or search tools.
The tests do not measure automatic selection of the revised skill, HTML production, or video rendering.

## Decision

Keep the shared core and optional research routing. Keep harness configuration separate from content rules.
Do not ship model-specific prompt variants based on this small run.
Audit conflicting instruction sources and verify reference permissions before attributing a failure to the model.
Use fresh held-out prompts and a clean configuration for the next causal comparison.

The branch contains the new structure and test tooling. The installed global skill and writing defaults remain unchanged.
