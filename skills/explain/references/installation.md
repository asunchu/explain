# Installation checks and terminal shortcuts

For the skill, shortcuts, global writing defaults, and local media tools together, run the repository's `install.sh`.
Its default mode configures Codex, Claude Code, and OpenCode with one shared installation.
Use `--dry-run` for a preview. Use `--core-only` to skip media preparation while retaining an existing runtime.
The full installer needs a complete checkout or the source snapshot downloaded by its bootstrap.
After installation, use `explain tools --json` to locate the prepared [toolchain](toolchain.md).


The complete skill includes its doctor, repair tools, and terminal launcher.
They use Python 3.10 or newer and its standard library.
The shortcut setup supports macOS and Linux. It does not require a repository checkout.

`EXPLAIN_SKILL` below denotes the absolute directory containing this installed `SKILL.md`.
Resolve that directory from the skill currently in use.

## Set up the terminal command

When the user requests shortcuts, preview the bundled setup:

```sh
python3 "$EXPLAIN_SKILL/scripts/install-shortcuts.py" --dry-run
```

Create the shortcut:

```sh
python3 "$EXPLAIN_SKILL/scripts/install-shortcuts.py"
```

Setup links `~/.local/bin/explain` to this installed skill's `scripts/explain` launcher.
It sets the launcher's owner executable bit. It does not change shell profiles.
Keep `~/.local/bin` on `PATH`. Use `--bin-dir /path/to/bin` for another directory.
Repeated setup accepts an existing link to the same launcher, including relative links.
A different existing link requires `--replace`. Regular files and directories are never replaced.
Use replacement only when the user authorizes changing the existing shortcut.
If the installation moves, run setup again with `--replace` to update the link.

A skill installer copies these tools; it does not automatically run shortcut setup.
For an immediate check without a terminal shortcut, run:

```sh
python3 "$EXPLAIN_SKILL/scripts/explain" doctor
```

## Check and repair

```sh
explain doctor
explain doctor --fix --dry-run
explain doctor --fix
```

The default reference is the skill copy that owns the launcher. This checks local consistency, not the latest published version.
The report shows its reference path and content fingerprint.
To compare against another checkout or an extracted release, select that source explicitly:

```sh
explain doctor --reference /path/to/source/skills/explain
explain doctor --reference /path/to/source/skills/explain --fix --dry-run
explain doctor --reference /path/to/source/skills/explain --fix
```

A plain doctor request authorizes a read-only check. Use repair only when the user requests it.
Repair preserves shared installation symlinks and instruction text outside existing marked blocks.
It verifies private backups before writing and checks for concurrent changes.
Rollback handles write failures and catchable cancellation. It preserves external edits and reports recovery conflicts.
Backup manifests record paths, hashes, and original permissions.
Backups use `$XDG_STATE_HOME/explain/backups`, or `~/.local/state/explain/backups` when unset.
Use `--backup-dir` to select another parent directory.

The doctor preserves extra package files and unmarked instructions. Ambiguous copies and invalid markers block repair.
Use `--harness codex`, `--harness claude-code`, or `--harness opencode` to select a harness.
Use `--project` to select its working directory and `--json` for the complete report.
No command downloads releases or installs dependencies.
File agreement does not prove active harness loading or correct model behavior.
