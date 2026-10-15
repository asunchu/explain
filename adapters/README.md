# Harness adapters

Keep one shared contract in `skills/explain/CORE.md`. Adapters handle loading and available tools, not different writing rules.

| Harness | Global default | Project instruction file |
| --- | --- | --- |
| Codex | `~/.codex/AGENTS.md` | `AGENTS.md` |
| Claude Code | `~/.claude/CLAUDE.md` | `CLAUDE.md` |
| OpenCode | `~/.config/opencode/AGENTS.md` | `AGENTS.md` |

Append the shared core to the chosen instruction file for always-on writing. Preserve unrelated instructions.
Update that copy when the skill changes; do not maintain separate prose variants.
Install the complete skill separately for detailed research and artifact guidance.
Global writing defaults work without a skill-load call. Test discovery separately from instruction following.

Map research to available local reads, Context7, official documentation fetches, or primary-source search.
Do not install a connector or add credentials merely because the skill names it.

## Model adapters

No model-specific adapter ships yet. Add one only after repeated failures on a pinned model and improvement on held-out prompts.
Use the resolved model identifier from harness metadata. Do not ask the model to guess its identity.
Record the tested version, failure, added instruction, and before/after evidence. Unknown identifiers use the shared core.
Do not select a model adapter by harness name.

## Verification

Record instruction hashes, model, harness version, tools, actual working directory, and skill-load events.
Installation and discovery are not behavior proof. A passing answer does not prove that the skill loaded.
Keep context injection, automatic discovery, and output quality as separate evaluation tracks.

Inspect startup hooks and output-style plugins when answers conflict with the shared contract.
A plugin that requires explanatory notes can compete with the rule to keep writing reviews internal.
Record that conflict before blaming the model or adding an adapter. Do not silently disable the user's plugins.
Pin the CLI executable as well as the model when multiple installations exist.
In OpenCode, loading a skill and reading its external reference files can require separate permissions.
Allow read access to both the installed path and its resolved target when needed; retain write restrictions.

Sources: [Codex](https://developers.openai.com/codex/skills/), [Claude Code](https://code.claude.com/docs/en/skills), [OpenCode](https://opencode.ai/v2/docs/instructions).
