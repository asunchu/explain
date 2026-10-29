# Pele 1.12.0: tests, live evaluations, and examples

The renderer update passes its local tests. The behavioral release check remains open.
Successful execution and instruction loading do not establish answer correctness.

## Renderer and artifact checks

- Fifteen renderer tests pass, including new checks for contrasting labels and opaque custom group fills.
- Three export protection tests pass.
- All 27 Python evaluation tests pass.
- The production dependency audit reports no known vulnerabilities.
- npm verifies Pele's registry signature and provenance attestation.
- Sixteen SVG variants render with the existing worker boundary.
- The SVGs parse as XML and contain no unresolved CSS variables, script elements, or external image elements.

The examples cover a request flow, a sequence diagram, and a class diagram.
They include light and dark themes, two layout targets, and a flow without a cache.
The class diagram is a teaching model of renderer inputs and outputs, not Pele's internal implementation.

The interactive HTML embeds its SVGs and selects pre-rendered variants.
Construct, theme, width, cache, and reset controls were exercised in the browser.
Desktop and mobile views were inspected. No page overflow appeared in the checked mobile viewport.

The Remotion video lasts 86.016 seconds at 1920×1080 and 30 fps, with H.264 video and AAC audio.
It includes local Kokoro narration and captions based on measured sentence audio lengths.
A sample was rendered before the full export. All six scenes, the opening frame, and the closing frame were inspected.
The complete file decodes without errors. Browser playback advanced without a media error.
The measured peak audio level is -2.4 dBFS after a six-decibel gain adjustment.
Narration was not auditioned. Pronunciation remains a listening check.

The examples remain in the ignored `output/pele-112/` folder.
They are not evidence that each tested harness independently produced a working artifact.

## Live evaluation method

Eight behavioral cases run three times per harness. A separate video-plan case also runs three times per harness.
Prompts do not invoke the skill. The behavioral tests inject the shared core and an exact-path router into project instructions.
The loading tests use the router without project core injection. Existing global defaults remain active.
This measures routed loading, not unassisted discovery in a clean environment.

Requested models remain `gpt-6.1-sol`, `claude-opus-5-5`, and `ollama/kimi-k3:cloud`.
Observed CLI versions are Codex 0.164.0, Claude Code 2.1.310, and OpenCode 2.1.4.
Codex's CLI version differs from the October 27 alpha build. No model fallback was used.

The initial Codex behavioral run completed two cases, then reported that the selected model was at capacity.
Its initial loading run timed out after 180 seconds without an answer.
Separate retry directories preserve those initial failures. Retry results must not replace the initial attempts in reliability counts.

| Harness | Behavioral responses | Routed loading reads |
| --- | --- | --- |
| Codex, separate retry | 24/24 completed | 3/3 read the local entrypoint, core, production guide, and video guide |
| Claude Code | 24/24 completed | 3/3 read those four local files |
| OpenCode / Kimi | 24/24 completed | 3/3 read those four local files |

The initial Codex attempts remain separate in the companion JSON report.
No final behavioral response triggers the descriptive sentence-length checker.
One Kimi video plan triggers a 46-word finding. Input hashes show no changes in the completed trials.
The rule files and pinned package match across the final runs; two renderer tests were added afterward.
The shared installed renderer was updated only after all live trials ended. Global writing defaults were unchanged.

## Concrete residual failures

Evidence paths are relative to the local evidence root in the companion JSON report.

| Trial | Finding |
| --- | --- |
| `loading-codex-retry/candidate/repeat-1/native-discovery` | The build plan combines generating and caching audio in one step. |
| `claude-code/candidate/repeat-1/local-evidence` | The answer says the loop makes exactly two attempts, although success can return early. |
| `loading-claude-code/candidate/repeat-2/native-discovery` | The stated binary search checks positions 4, 2, and 3 for Oslo, which begins at position 5. The trace is wrong. |
| `loading-claude-code/candidate/repeat-2/native-discovery` | The narration says each write must update the index. An update to an unrelated field need not change it. |
| `loading-claude-code/candidate/repeat-3/native-discovery` | Checking only the successor after finding Maya cannot rule out another Maya immediately before it. |
| `opencode/candidate/repeat-1/heldout-installation` | The answer calls installation the only way to settle the question, although matching documentation could also provide evidence. |
| `loading-opencode/candidate/repeat-2/native-discovery` | A descriptive sentence has 46 words. The plan also combines measuring audio and setting scene lengths. |
| `loading-opencode/candidate/repeat-3/native-discovery` | Halving candidate counts is presented as an exact search trace without actual key comparisons. |

The primary assistant reviewed the answers. No independent judge reviewed this run.
Sentence-length flags do not grade factual accuracy or establish STE compliance.
The report gives concrete residual failures rather than an unsupported overall pass rate.

## Evidence

- [Machine-readable results](2026-10-29-pele-112-evaluations.json)
- [Dependency verification](../../security/pele-2026-10-29.md)
- Local artifacts: `output/pele-112/README.md`

No commit, push, or publication was performed for this update.
