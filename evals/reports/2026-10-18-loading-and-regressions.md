# Automatic loading and behavioral recheck — October 18, 2026

## Release decision

Do not push this as fully validated. The local entrypoint loads reliably in this sample, but Kimi still skips supporting files.
The original behavioral rubric passed for all 62 completed final trials. Ten Kimi trials remain incomplete because of an Ollama quota limit.
Additional review found an unsupported Kimi claim and sentence-length failures in a video plan.
These concerns remain release blockers even though the narrow behavioral rubric passed.

## Final behavioral matrix

| Harness / model | Original five cases | Additional three cases | Completed / planned |
| --- | --- | --- | --- |
| Codex / gpt-6.1-sol | 15/15 passed | 9/9 passed | 24/24 |
| Claude Code / claude-opus-5-5 | 15/15 passed | 9/9 passed | 24/24 |
| OpenCode / ollama/kimi-k3:cloud | 10/10 completed passed | 4/4 completed passed | 14/24 |

Each case runs three times in a fresh workspace. No user prompt names or invokes the skill.
The prompts include ordinary uses of the verb “explain.” Persistent instructions supply the core and artifact router.
The additional cases came from an earlier held-out set; they are now regression cases, not new held-out evidence.
The primary assistant reviewed the answers and traces. There was no independent judge.
All 62 completed fixture and skill inventories remained unchanged; the inventory excludes Git internals.
Relevant source reads were checked. The offline cases made no observed web-tool calls.

The prior Kimi runbook additions, writing-review announcements, long documentation sentence, and identifier omission did not recur in these 14 completed trials.
This is partial evidence, not proof that the remaining ten trials pass or that all future answers comply.

## Automatic loading

These tests supply only a path-specific router, without injecting the shared core into the project instruction file.
Existing global instructions remain active. Each prompt requests a video plan, not a render.

| Harness | Local entrypoint selected | All four required local files read |
| --- | --- | --- |
| Codex | 3/3 | 3/3 |
| Claude Code | 3/3 | 3/3 |
| OpenCode / Kimi | 3/3 | 1/3 |

The four files are SKILL.md, CORE.md, references/production.md, and VIDEO.md.
Kimi repetition 2 skipped production.md and read only lines 30–43 of VIDEO.md.
Kimi repetition 3 skipped CORE.md. These omissions prevent a claim of complete automatic loading.
The marked global/project defaults normally contain the core, but this cold-loading probe tests whether the reference chain works independently.

Two native-selection controls omitted the router. Claude selected its global copy, while Kimi selected the local copy.
Each control ran once, so neither establishes a reliable native-selection rate.
The tested fix uses persistent path-specific routing; it does not change the harness's native skill resolver.

## Additional Kimi findings

- Behavioral repetition 1, version-gap: the answer claims that upgrading the declaration or obtaining documentation requires network access. The local files do not establish that requirement.
- Loading repetition 3: the video plan has a 26-word sentence beginning “The brief omits some details.” The limit is 25.
- The same plan combines multiple audio-check actions into one bullet. Passing entrypoint selection does not validate the plan's writing.
- Required supporting-file reads remain incomplete in two loading trials, as recorded above.

The behavioral JSON preserves the frozen rubric score and records supplemental concerns separately.
Do not present the 14 passed rubric checks as unconditional Kimi readiness.

## Changes

- Use one shared core across models, with a 12–18 word target below the hard sentence limits.
- Preserve each supplied identifier and fact when rewriting.
- Keep warnings outside numbered steps and prohibit added or repeated actions in supplied procedures.
- Suppress writing-check announcements for rewrites, including progress messages.
- Route artifact requests to the exact installed entrypoint, avoiding a different global copy with the same name.
- Synchronize the core and router into a marked instruction block while preserving unrelated content.
- Freeze skill files for each experiment and exclude runtime dependencies and caches from trial copies.
- Add a sentence-length review helper with tests for code, quotes, links, and sentence boundaries.

The helper flags prose for manual review. It does not enforce model output or certify STE compliance.
It skips headings, tables, code, and protected quotations; those still need manual review when relevant.

## Infrastructure and reproducibility

Codex CLI 0.163.0 received an explicit gpt-6.1-sol flag. Equivalent resolved model metadata was not exposed.
Claude Code 2.1.302 reported claude-opus-5-5 in all 24 completed behavioral traces.
All 14 completed OpenCode session exports confirm Ollama / kimi-k3:cloud and the expected working directory.
OpenCode CLI is 2.0.32. Claude's explanatory style plugin was disabled for test processes only.
Saved model settings, global installations, and global instruction files were not changed.

The final Kimi run stopped on HTTP 429 during repetition 2, heldout-installation.
One trial is blocked and nine were not started. There was no model fallback or quota retry.
The local remaining-kimi.json file records the ten cases and frozen candidate hash for a later continuation.

Exploratory candidates preceded the final run. They exposed a long sentence and an omitted identifier.
Their superseded controllers were stopped, their partial traces retained, and their outcomes excluded from the final matrix.
No trial was silently replaced. This task used local authenticated CLIs and provider quota.

The three writing runs use the same frozen core. The loading runs use the same skill content and router.
Raw traces remain local because they can include account and workspace details.
The committed JSON contains reviewed judgments and hashes, not raw private traces.

## Validation and limits

24 unit tests passed. Package validation, skill validation, and whitespace checks passed.
No model-specific instruction variants were introduced.
The remaining work is to finish the quota-blocked Kimi trials and verify a fix for skipped supporting files and the broader output concerns.
This run does not validate fresh HTML interactions, rendered video, Context7 calls, or multi-turn persistence.
No push, merge, or website publication occurred.

Final core SHA-256: `b6163e737c6f9d6b5cc15f8898f16bd4203aca66cad57130d7b01999ad279e39`.
