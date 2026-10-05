# Behavioral evaluations

These evaluations ask whether an agent using Explain makes good decisions and delivers what was requested. They do not substitute installation checks or rendering the bundled example for a fresh behavioral run.

`cases.json` is the harness-neutral source of prompts and observable criteria. `scripts/evaluate.py` prepares trials and summarizes reviewer judgments using only Python's standard library. It does not invoke models, spend API credits, or automatically judge answers. No behavioral pass is claimed by adding this suite.

## Coverage

| Tier | Cases | Purpose |
| --- | --- | --- |
| core | 9 | Brief answers, diagrams, explicit prose/Manim, recommendations/script only, false premises, unavailable local TTS, unauthorized paid narration |
| artifact | 2 | Cache controls with numerical endpoints; offline software-factory story with failure and repair |
| media | 2 | Fresh 30-second narrated export; visual-only revision reuses audio |
| discovery | 4 | Implicit Explain activation; an unrelated arithmetic request stays minimal |

An explicit request wins over the typical format for a topic. A narrative can be interactive HTML when requested. Video tests require exported, playable media, not just a storyboard or source. The 27–33 second tolerance is a test acceptance band, not a new skill rule.

## Run a trial

1. Validate definitions and the reporter:

   ```sh
   python3 scripts/evaluate.py validate
   python3 -m unittest discover -s evals -p 'test_*.py' -v
   ```

2. Prepare a new directory outside the repository. Use your actual model and harness versions; the example values below are placeholders to replace:

   ```sh
   python3 scripts/evaluate.py prepare \
     --harness codex --model YOUR_MODEL --harness-version YOUR_VERSION \
     --tier core --out /tmp/explain-eval-codex-01
   ```

   Supported harness labels: `codex`, `claude-code`, `opencode`. Use `--tier artifact`, `media`, `discovery`, or `all`; use repeated `--case CASE_ID` to select specific cases within that tier. Existing directories are refused to avoid overwriting evidence. The run contains a candidate skill snapshot and hashes, prompts, separate reviewer rubrics, empty work directories, and pending results.

3. Use the [installation instructions](../README.md#install) to make the **candidate snapshot** available to the chosen harness. Verify it loads this version rather than an older global copy. Start a fresh session in each case's `work/` directory. For core/artifact/media trials explicitly invoke Explain using the native harness syntax (`$explain`, `/explain`, or a natural-language instruction to use Explain), then supply the unmodified `prompt.txt` contents. Keep the native invocation in the transcript. Do not provide `review.md`, expected formats, other trial answers, or results to the tested agent.

   For discovery trials, supply only `prompt.txt`, with no skill invocation, path, or extra routing instructions. Record the harness's skill-load event. Lack of an observable activation trace is blocked, not proof of implicit selection. Discovery and explicitly invoked trials measure different things.

4. Read each case's setup before running it. Enforce unavailable capabilities for `local-tts-unavailable`; a prompt alone is not a sandbox. Use fresh temporary workspaces and no real secrets or production access. Normal local setup/model downloads are permitted in the video case, but there is no authorization for paid TTS or publication. Run `visual-only-revision` in a copy of the completed video trial and record audio hashes before and after. If an environment cannot satisfy the setup, record the blocker.

5. Save the full prompt, response, and action/tool transcript inside the run directory, plus generated artifacts, browser observations/screenshots, and relevant media logs. Record model/version and reviewer identity in `results.json`. Review without changing the tested output. For each criterion assign `pass`, `fail`, `blocked`, or leave `pending`, and give concrete evidence (file + location, observed control behavior, measured value, or reason blocked). Evidence is a reviewer assertion; the reporter checks its presence, not its truth.

   Example of a **rating format**, not a real result:

   ```json
   {
     "id": "brief-definition",
     "observed_format": "prose",
     "transcript": "brief-definition/transcript.txt",
     "criteria": {
       "format": {"status": "pass", "evidence": "transcript.txt: final answer is prose; full tool trace contains no artifact creation."},
       "length": {"status": "pending", "evidence": ""},
       "mechanism": {"status": "pending", "evidence": ""},
       "tradeoff": {"status": "pending", "evidence": ""}
     }
   }
   ```

6. Summarize the run:

   ```sh
   python3 scripts/evaluate.py report /tmp/explain-eval-codex-01/results.json
   ```

   Exit codes: **0** all selected cases pass, **1** at least one fails, **2** pending/blocked cases remain without failures, **3** invalid records. The report always shows selected cases versus the full suite. Removing a selected result, omitting a criterion, claiming a pass without evidence/transcript, or changing the candidate skill invalidates the record. A passing subset is not a passing full suite.

## Review actual artifacts

- **Prose:** check the causal explanation and factual qualifications, not particular words or headings. Count words only when the prompt asks for a limit.
- **Diagrams:** render them. Check arrow direction, labels, and whether the same entities retain their meaning.
- **HTML:** open it in a real browser. Exercise keyboard controls, endpoint and intermediate parameter values, reset, and reduced motion. Disable network for offline cases. Compare displayed results with the formula in the rubric; inspect desktop and narrow layouts. Static HTML string matches do not prove interactions work.
- **Video:** run `ffprobe -v error -show_format -show_streams -of json VIDEO.mp4` and `ffmpeg -v error -i VIDEO.mp4 -f null -`. Inspect scene-boundary/dense frames, listen to narration and its ending, and check subtitle timing against speech. Decode success alone does not establish good pronunciation or synchronization. Mark criteria blocked when required inspection is unavailable, even if the agent correctly discloses that limitation.
- **Boundaries:** inspect actions, not just promises in the final response. A statement of “local only” is not proof that no cloud call occurred. Never use live paid calls to test a no-spending case.

A case passes only when **all** criteria pass and its observed format is acceptable. Any failure makes the case fail; otherwise pending or blocked checks prevent a pass. Preserve first attempts and failed runs rather than silently rerunning until success.

## Compare skill revisions and harnesses

Use identical prompts, model/settings, capabilities, and budgets for before/after trials in fresh sessions. Repeat each selected case three times to expose variability; report the per-case results and blockers, not only an overall percentage. For native discovery, compare with/without the skill installed separately from explicit skill-invocation trials. Do not change models and attribute the difference to a skill edit.

Run the core suite in each target harness before claiming behavioral portability. Artifact, media, and discovery results should be reported separately. A recommendation for release confidence is zero core failures across three repetitions per harness, followed by the relevant artifact/media cases; this is a practical regression gate, not a statistical guarantee. Use a second independent reviewer for subjective visual/audio judgments when practical.

CI runs only deterministic definition/reporter checks. Real harness trials require installed harnesses, model access, artifact tools, and review. Keep transcripts local by default; redact credentials, personal paths, and private inputs before sharing sanitized results in a PR. Never relabel synthetic reporter-test fixtures as skill behavior evidence.
