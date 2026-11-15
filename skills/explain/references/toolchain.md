# Use the installed local toolchain

The full installer prepares one shared media runtime for all three harnesses.
Run `explain tools --json` to find its paths. This reads configuration; it does not download packages.
The receipt lives at `$XDG_STATE_HOME/explain/toolchain.json`, or `~/.local/state/explain/toolchain.json` when unset.
Its runtime record includes `video`, `diagrams`, `python`, `venv`, `models`, and `browser`.
The `executables` record contains the selected Node.js, npm, FFmpeg, and ffprobe paths.
Use these explicit paths when the system defaults differ. The installer does not activate the media environment globally.

The installed diagram wrapper already links to the prepared Pele dependency.
Use its normal command from [diagrams.md](diagrams.md).
Its disposable worker retains the same limits and empty environment.

For a new video project, reuse the runtime paths instead of installing packages again.
Link the runtime's `video/node_modules` into the artifact project as `node_modules`.
Link its `.venv` as `.venv` and its `models` directory as `models` when the project uses the bundled example scripts.
Use the returned `browser` path as Remotion's `browserExecutable` to avoid another browser download.
Keep the artifact source, script, scene audio, and exports in that artifact's folder.
Do not edit the shared runtime or use its smoke project as the artifact project.

The installer checks an actual diagram, local Kokoro synthesis, and a short Remotion export.
It verifies model hashes, audio samples, media streams, and full decoding.
These technical checks do not establish narration pronunciation or teaching quality.
No speech API key is required. Initial downloads use public package and model services.
