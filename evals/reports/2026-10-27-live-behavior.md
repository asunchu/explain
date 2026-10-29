# Live behavior recheck: October 27

The final candidate improves loading and uncertainty handling. It does not clear the release check.
All runs use natural prompts without a skill invocation. The models remain unchanged from the previous comparison.

| Harness | Requested model | Behavioral responses | Routed loading |
| --- | --- | --- | --- |
| Codex | gpt-6.1-sol | 24/24 completed | 3/3 read all required files |
| Claude Code | claude-opus-5-5 | 24/24 completed | 3/3 read all required files |
| OpenCode | ollama/kimi-k3:cloud | 24/24 completed | 3/3 read all required files |

Completion means a successful command returned an answer. It does not mean every claim or instruction passed review.

## Changes under test

- Require the installed core to be read, even when global writing defaults exist.
- Start unresolved yes/no answers with uncertainty rather than a misleading negative.
- Apply single-action rules to build and verification plans.
- Check sentence length before delivery, including closing recommendations.
- Validate teaching examples, count claims, and limits before writing video scripts.
- Record empty responses separately from infrastructure errors. Continue independent cases without retrying an empty response.
- Use the selected OpenCode executable for session export.
- Exclude installed dependencies and caches from trial preparation.

The runner changes do not establish a fix for the upstream OpenCode tool-format failure.
That failure did not recur in this final run.

## Improvements observed

All 18 answers about missing version evidence opened with uncertainty. The earlier misleading “No” openings did not recur.
All nine recovery runbooks preserved six separate actions and placed the warning before restoration.
The sentence checker found no over-limit sentences in the 72 behavioral responses.
All nine loading trials read the local entrypoint, core, production guide, and video guide.
All 81 trials preserved the input files covered by the runner's hashes.

## Remaining failures

Evidence paths below are relative to the local evidence root in the JSON report.

| Failure | Evidence | Implication |
| --- | --- | --- |
| Combined actions in a video plan | `final-loading-codex/candidate/repeat-1/native-discovery/answer.md`: “Generate and cache narration separately for each scene.” | Reading the rule does not ensure each plan step has one action. |
| Overbroad index maintenance claim | `final-loading-claude-code/candidate/repeat-1/native-discovery/answer.md`: “every write must update it” | An update to an unrelated field need not change that index. |
| Same factual error in Kimi narration | `final-loading-opencode/candidate/repeat-1/native-discovery/answer.md`: “each write must update the index” | The video guidance does not reliably prevent universal claims. |
| Combined build and check actions in Kimi plans | `final-loading-opencode/candidate/repeat-3/native-discovery/answer.md` combines measuring and setting timing, plus rendering and inspecting. | The single-action rule remains unreliable. |
| Long sentence in a Kimi plan | The same response has a 26-word sentence listing sorted entries and row pointers. | The sentence check still fails in richer output. |
| Unsupported installation wording | `final-opencode/candidate/repeat-2/heldout-installation/answer.md` refers to an “installed 1.8.0 package state” after stating installation is unknown. | A correct opening can still lead to a contradictory detail. |
| Missing source filename | `final-opencode/candidate/repeat-2/heldout-local/answer.md` gives line numbers without naming `sender.py`. | The answer does not fully identify its local source. |
| Overstated exception timing | `final-opencode/candidate/repeat-3/local-evidence/answer.md` says a raised exception exits before the second attempt. | An exception can also arise on the second attempt. |

These are concrete residual failures, not an exhaustive score for every possible claim.
Do not promote the completion counts to an overall behavioral pass rate.

## Method and limits

Eight behavioral cases ran three times per harness. One routed video-plan case also ran three times per harness.
Each final run used the same skill snapshot. Earlier exploratory runs remain separate and do not contribute to the table.
The entrypoint changed after exploratory loading revealed that Kimi could substitute ambient defaults for the core read.

Behavioral trials inject the shared core and an exact-path router into project instructions.
Loading trials use that router without injecting the project core. Existing global defaults remain active in both groups.
This checks routed loading, not native discovery in a clean environment.

The primary assistant reviewed the answers and loading traces. No independent judge reviewed this run.
The sentence checker skips protected text and is not a full STE validator.
No video was rendered, and no interactive artifact was exercised. This is not a full run of the 23-case suite.

All 27 Python unit tests passed. Repository validation and all 23 evaluation definitions also passed.
The skill validator and whitespace checks passed. No model fallback or global configuration change was used.

The [machine-readable report](2026-10-27-live-behavior.json) records versions, snapshot hashes, answer hashes, and evidence paths.
Changes remain on the existing branch. Nothing was pushed.
