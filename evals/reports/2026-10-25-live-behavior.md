# Live behavioral evaluations — October 25, 2026

## Result

The skill loads through persistent routing across all three harnesses in this sample.
Answer quality still has gaps. Successful execution and file loading do not count as behavioral passes.
No push, model fallback, or global configuration change occurred.

| Harness / requested model | Behavioral answers completed | Correct local entrypoint and all four required files |
| --- | --- | --- |
| Codex / gpt-6.1-sol | 24/24 | 3/3 |
| Claude Code / claude-opus-5-5 | 24/24 | 3/3 |
| OpenCode / ollama/kimi-k3:cloud | 23/24 | 3/3 |

The behavioral run uses eight existing cases with three repetitions each.
The loading run uses one video-planning case with three repetitions per harness.
No user prompt names or invokes the skill. Some prompts use the ordinary verb “explain.”
All 81 trial workspaces retain unchanged fixture and skill files, excluding Git internals.
The 71 completed behavioral answers include actual source reads for the relevant local cases and official-documentation cases.

## Findings

### Uncertainty still needs attention

Claude's second version-gap answer starts with “No.” It then says the available files cannot establish the answer.
Kimi's first caching answer starts with “No” and then says the files cannot settle the question either way.
Kimi's first version-gap answer also starts with “Short answer: no,” before qualifying that the files cannot establish retry behavior.
These openings can imply a negative finding where the evidence supports only uncertainty.

Evidence: `claude-compatible/candidate/repeat-2/version-gap` and `opencode-path-fixed/candidate/repeat-1/{version-gap,heldout-installation}`.

### Kimi exceeds the sentence limit

The third caching answer contains a 27-word sentence:

> To verify, you would need to inspect the installed package (for example, after running the package manager install) or check the release notes for version 1.8.0 specifically.

The descriptive limit is 25 words.
The sentence checker finds no other long prose in completed answers under its exclusions.
It skips tables, headings, protected quotations, and code. This is not a full writing-compliance score.

Evidence: `opencode-path-fixed/candidate/repeat-3/heldout-installation`.

### Video plans combine actions

All three models produce at least one video-plan step with multiple actions.
Examples include Codex's “Generate and cache,” Claude's “Measure each audio clip, then set,” and Kimi's “Decode the full video and inspect.”
These violate the shared rule requiring one instruction per procedure step.
The nine queue-recovery runbooks preserve the six supplied actions, their order, and a warning before restoration.

Evidence: `loading-codex/candidate/repeat-3/native-discovery`, `loading-claude-code/candidate/repeat-3/native-discovery`, and `loading-opencode/candidate/repeat-3/native-discovery`.

### Video accuracy needs a separate review

Kimi's third plan uses a million-row example despite the request for a small example.
It calls about twenty comparisons the “real figure” for a B-tree lookup, based on a binary logarithm.
That calculation does not establish the actual database lookup cost or B-tree depth.
The same plan omits the storage tradeoff. Kimi's first plan also omits storage.
Claude's third plan omits storage and claims that every write must update the index.
That statement needs qualification because an update can leave the indexed values unchanged.
Codex's plans explicitly describe a simplified example and distinguish the mechanism from measured speed gains.

These findings show why file-loading success cannot substitute for checking the explanation itself.

### OpenCode returns no answer in one trial

The second version-gap trial exits with code zero but returns no answer.
Its saved session contains an encoded tool call as text rather than an executed tool call.
No quota error appears in the saved trace or session export.
This establishes a response/tool-format failure; it does not establish whether the model, provider, or harness caused it.
The failed attempt remains intact. The remaining twelve cases ran once, without retrying or replacing that attempt.

Evidence: `opencode-path-fixed/candidate/repeat-2/version-gap`.

## Loading and test conditions

All nine loading trials read the local `SKILL.md`, `CORE.md`, `references/production.md`, and `VIDEO.md`.
The earlier Kimi result was 1/3 for these four files; this run reaches 3/3.
These small samples do not establish a reliable long-term rate or show that the Pele upgrade caused the difference.

Behavioral trials inject the shared core and exact-path router into persistent project instructions.
Loading trials inject the router without the shared core. Existing global instructions remain active.
Thus, this tests routing without explicit user invocation, not native discovery without routing or a clean-room installation.
The core hash remains `b6163e737c6f9d6b5cc15f8898f16bd4203aca66cad57130d7b01999ad279e39`.
The skill snapshot includes the Pele 1.10.0 dependency update.

| Harness | CLI version |
| --- | --- |
| Codex | 0.164.0-alpha.11.1 |
| Claude Code | 2.1.310 |
| OpenCode | 2.1.4 |

Claude traces confirm `claude-opus-5-5`. OpenCode exports confirm Ollama `kimi-k3:cloud`.
Codex receives the explicit `gpt-6.1-sol` argument; equivalent resolved-model metadata is not asserted.
Claude's explanatory-style plugin is disabled only for these evaluation processes, matching the prior experiment.

The first Claude launch used an older CLI and failed its model compatibility check.
A compatible, already installed CLI completed the run. No installation or model change was necessary.
The first OpenCode setup failed because its executable was outside PATH. The corrected run uses its explicit installed path.
Both setup failures remain in the local evidence folder and are excluded from the trial counts above.

## Evidence and limits

Raw evidence: `$LOCAL_EVIDENCE/explain-live-2026-10-25/`.
Each run retains prompts, frozen inputs, CLI metadata, transcripts, answers, and file hashes.
The companion JSON records completion, sentence flags, and evidence paths. It is not an automatic semantic grader.
The primary assistant reviewed outputs and tool calls; there was no independent judge.
These are reused regression prompts, not fresh held-out cases.
This run does not execute all 23 cases in `evals/cases.json`, render video, test interactive HTML, or test multi-turn persistence.
No skill-rule changes were made during the experiment.

The next fixes should address uncertainty wording, one-action procedure steps, and factual checks on video plans.
Investigate the OpenCode response-format failure separately from instruction following.
