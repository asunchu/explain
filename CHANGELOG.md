# Changelog

## v0.2.0 — 2026-10-18

- Make clear technical English the default, with a shared writing contract for Codex, Claude Code, and OpenCode.
- Add research routing that prefers local evidence and relevant primary sources. Context7 remains optional.
- Add paired evaluation tooling and a [90-trial report](evals/reports/2026-10-15-grounded-defaults.md). Sampled results improve, but failures remain.
- Add [Pele 1.6.0](skills/explain/references/diagrams.md) for local Mermaid rendering. The wrapper disables links and images, bounds resources, and preserves existing output files.
- Record a [dated security review](security/pele-2026-10-18.md). The review finds no confirmed critical or high vulnerability in the tested runtime path. Integration controls reduce residual resource risks.
- Add the [Home HQ example](examples/pele-diagram/). Its compact layout uses explicit colors and fonts for SVG and PNG exports.
- Check export fonts before replacing assets. Regression tests preserve existing files when font input fails.
- Update the [Explain film](examples/explain-video/) with a clear-writing script and Remotion visuals. Include captions, a transcript, and editable source.
- Add clean Linux installation and rendering checks. Installation checks remain separate from agent behavioral evaluations.

Release assets include the complete skill with license notices, the current film, and the standalone software-factory example.
They also include the Home HQ PNG, the editable Pele example, and `SHA256SUMS`.
Build dependencies and font files are installed separately.

## v0.1.0 — 2026-10-03

- Publish the portable Explain skill for Codex, Claude Code, and OpenCode.
- Choose prose, diagrams, interactive HTML, or narrated video according to the learning goal and requested format.
- Include the standalone [software-factory walkthrough](examples/software-factory/), with repair cycles and human decisions.
- Include the first Explain film with captions, local Kokoro narration, and editable production files.
- Validate skill references, artifact links, media timing, and browser interactions. These checks do not establish cross-harness behavioral compatibility.

Original material uses the MIT license. Dependencies retain their own terms; see [THIRD_PARTY.md](THIRD_PARTY.md).
