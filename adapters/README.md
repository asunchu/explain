# Harness adapters

The repository's `bash install.sh` configures all three harnesses together.
It enrolls or updates managed defaults, creates shared skill aliases, and sets up local media tools.
It checks conflicts before downloads and stages media checks before changing active configuration.
Use `--dry-run` to preview the full setup or `--core-only` to omit media dependencies.
Configuration backups include original file contents and symlink targets.
PATH setup respects `ZDOTDIR` and Bash login-profile precedence.
The private media environment stays outside the global PATH.
Shell PATH changes take effect in a new terminal. Fresh harness sessions load the new defaults.

Keep one shared contract in `skills/explain/CORE.md`. Adapters handle loading and available tools, not different writing rules.

| Harness | Global default | Project instruction file |
| --- | --- | --- |
| Codex | Nonempty `~/.codex/AGENTS.override.md`, otherwise `~/.codex/AGENTS.md` | `AGENTS.md` |
| Claude Code | `~/.claude/CLAUDE.md` | `CLAUDE.md` |
| OpenCode | `~/.config/opencode/AGENTS.md` | `AGENTS.md` |

Copy the shared core into the chosen instruction file for always-on writing:

```sh
python3 scripts/sync-defaults.py /path/to/AGENTS.md
```

Use `CLAUDE.md` for Claude Code. The script replaces only its marked block and preserves other text.
It does not install the skill or change model settings.
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

For a controlled Claude test, pass `--disable-style` to the evaluation runner.
This disables `explanatory-output-style@claude-plugins-official` for that process only.
Verify startup events; do not infer that a setting suppressed a hook merely because the argument was accepted.

## Automatic artifact loading

Install the complete skill, then synchronize the defaults with its exact directory:

```sh
python3 scripts/sync-defaults.py /path/to/AGENTS.md --skill-path /path/to/skills/explain
```

Use CLAUDE.md for Claude Code. The marked block contains shared writing rules and a short artifact router.
The router reads the exact local entrypoint instead of relying on a name that can resolve to a global copy.
It covers video plans as well as finished artifacts. Ordinary rewrite requests do not require artifact guidance.
Keep the same router across models. Re-run synchronization if the installation moves.

This is automatic loading through persistent instructions, not guaranteed native skill selection.
Evaluate native discovery without the router and routed loading with it; report the two results separately.
The evaluation runner exposes `--route-skill` for this distinction.
Local trial copies exclude dependency folders and caches so they do not enter the fixture inventory.

## Installation diagnostics

Use the bundled [shortcut setup](../skills/explain/references/installation.md) to enable `explain doctor` from an installed skill.
The default reference is the skill copy that owns the command, not the latest published release.
The repository entrypoint `python3 scripts/doctor.py` uses the same bundled tools.
Pass `--project /path/to/project` when the harness starts elsewhere.
The check walks from that directory to the nearest Git worktree root.
Without a Git root, it checks ancestors through the filesystem root.
It does not search child projects.

| Harness | Candidate skill roots |
| --- | --- |
| Codex | Global `.agents/skills`, legacy `$CODEX_HOME/skills`, and project `.agents/skills` |
| Claude Code | `$CLAUDE_CONFIG_DIR/skills` and project `.claude/skills` |
| OpenCode | Global and project OpenCode, Claude-compatible, and `.agents/skills` locations |

`CODEX_HOME` defaults to `~/.codex`. `CLAUDE_CONFIG_DIR` defaults to `~/.claude`.
OpenCode's global config root uses `$XDG_CONFIG_HOME/opencode`, or `~/.config/opencode` when unset.
`OPENCODE_CONFIG_DIR`, when set, adds a custom candidate root.
These are candidate locations; the check does not resolve harness settings or precedence.
Use `--skill-path` for another known installation, including an enterprise or plugin copy.
The check does not enumerate plugin stores or cloud installations.

The JSON report includes searched roots, aliases, content fingerprints, and changed, missing, or extra package files.
It excludes dependency folders, model folders, Python caches, and `.DS_Store`.
Broken links, unreadable files, and unexpected file types produce findings.
Equal independent directories still count as separate copies. Symlinks to the same directory count once.

The doctor reads global instruction files and common project instruction files along the checked ancestor path.
It compares only the block between `explain-writing-default` markers with `CORE.md`.
It checks the router generated by `sync-defaults.py` separately, including whether its target exists.
Unmarked instructions are reported as unmanaged. Their content is not printed or compared.
Reports include local paths and hashes, but omit instruction bodies.

The default check makes no changes. Redirect `--json` output to a local file when needed.

### Repair existing copies

Use `--fix --dry-run` to preview file updates without creating backups or target files.
Use `--fix` to apply those updates from the selected reference copy.
The command requires one unambiguous installation for each selected harness.
It updates a shared target once and preserves symlink aliases.
It updates existing marked defaults blocks with the shared core and a router to that target.
It preserves every byte outside the marked span, including original line endings.
It leaves extra files, dependency directories, and unmanaged instructions unchanged.
Missing installations, invalid markers, unreadable paths, and ambiguous copies require manual resolution.

Every applied repair stores private backups before changing any destination.
The backup manifest records each destination, its original permissions, original content hash, and proposed content hash.
New files have no original backup; the manifest records them as new.
Backup files use mode `0600` inside a directory with mode `0700`.
The command rechecks the source, installation, aliases, and destination contents before writing.
It attempts to restore original contents and permissions if a write fails.
It reports the backup directory and rollback state when recovery is incomplete.

A successful repair can leave findings when extra package files remain.
The JSON report separates repair status from the final doctor result.
A repeated repair makes no changes when the files and defaults already match.
The command does not download updates, install dependencies, enroll unmarked instruction files, or delete duplicate copies.
A matching report establishes file agreement within this scope. Use harness traces to verify actual loading.
