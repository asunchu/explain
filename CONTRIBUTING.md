# Contributing

Open an issue or pull request with the request you tried, the harness/model, the actual outcome, and the outcome you expected. Remove private inputs and credentials.

Keep `skills/explain/SKILL.md` portable and concise. Put detailed provider or animation guidance in references. Prefer changes supported by a real example over new universal rules.

Before submitting:

1. Run `python3 scripts/validate.py`.
2. Exercise changed HTML interactions at desktop and mobile widths, including keyboard and reduced motion.
3. For video changes, render a sample before the full film and run the example's verification command.
4. Record what you tested; do not call installation discovery a behavioral test.

Useful format-selection checks: a short definition should remain prose; a relationship question should get a clear diagram; adjustable scenarios should get meaningful interaction; an explicit video request should get a playable video. An explicit medium always wins. Outcomes can vary with model and available tools.

Do not commit model weights, dependency directories, credentials, personal paths, or unrelated artifacts. Contributions are provided under this repository's MIT license.
