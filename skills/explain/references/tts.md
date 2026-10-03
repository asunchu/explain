# Narration selection and cost

Price snapshot checked 2026-10-03; USD, before taxes, retries, other services, and applicable plan minimums. Recheck the selected provider before paid generation. “Best” depends on language, pronunciation, voice preference, expression, and budget. These are recommendations from documented capabilities and prices, not a listening benchmark performed during skill creation.

## Recommendations

- **Cheapest without an API bill:** local Kokoro-82M. Apache-2.0 weights, 82 million parameters. You still pay in local compute, setup time, and model storage. Check language and voice support before choosing it.
- **Best cost/convenience starting point:** hosted Kokoro on DeepInfra. Its model page currently lists **$0.62 per million input characters**. This is the lowest ongoing hosted character rate among the options checked here, not a claim to have surveyed every provider.
- **Premium expressive option:** ElevenLabs. Audition a short passage containing the actual names, acronyms, numbers, and emotional tone. Compare it with Kokoro before paying more for a whole production.

## Comparable character-based prices

The example uses 5,000 characters, roughly five minutes only if narration averages 1,000 characters/minute. Actual duration varies. This excludes free allowances and promotional discounts so the ongoing rates can be compared.

| Provider/model | Published unit rate | 5,000-character synthesis |
| --- | --- | --- |
| Local Kokoro | $0 API charges | $0 API charges; local compute extra |
| DeepInfra Kokoro | $0.62 / 1M characters | $0.0031 |
| Google Standard / WaveNet | $4 / 1M characters after allowance | $0.02 |
| Deepgram Aura-1 | $15 / 1M characters | $0.075 |
| Deepgram Aura-2 | $30 / 1M characters | $0.15 |
| ElevenLabs Flash/Turbo API offer | $0.05 / 1,000 characters | $0.25 |
| ElevenLabs Multilingual v2/v3 API offer | $0.10 / 1,000 characters | $0.50 |

ElevenLabs also sells subscription credit plans with different model multipliers. The checked general pricing page lists Starter at $6/month with 30,000 credits and commercial licensing; promotions and API offers can differ. Use the actual account's current billing model instead of mixing credit-plan and pay-as-you-go prices. Free-tier output is not automatically licensed for commercial publication. Do not infer pricing for newer models from this table.

## Production workflow

1. Choose the language and voice explicitly. Make a pronunciation list for product names, acronyms, mathematical notation, and numbers. Keep the written transcript human-readable.
2. Generate a representative short sample before a long job. Compare clarity, pronunciation, pacing, and expression. If audio playback is unavailable, do not claim a voice has been auditioned.
3. Synthesize each scene separately and retain the exact input text, model, voice, parameters, and returned audio. Cache unchanged scenes. Estimate total characters including expected retakes against the authorized budget.
4. Measure the generated audio and fit animation to it. Prefer WAV for editing; encode for distribution at export. Use actual timestamps or forced alignment for captions requiring word precision.
5. Inspect the final mix. Avoid clipping, abrupt cuts, and background music competing with the voice. Regenerate only scenes with demonstrated problems.

For local Kokoro, follow the [author's repository](https://github.com/hexgrad/kokoro) and [model card](https://huggingface.co/hexgrad/Kokoro-82M). Its documented Python pipeline uses `KPipeline`, `soundfile`, and language-specific phonemization dependencies such as `espeak-ng`. Use a project virtual environment and verify platform-specific installation instructions. Initial model/package downloads require connectivity; offline inference requires those assets already cached.

Do not use an unofficial consumer speech endpoint as a production “free TTS” guarantee. Prefer a supported local model or a documented provider API. Keep cloud requests limited to the intended narration text and keep credentials server-side.

## Primary pricing sources

- [DeepInfra Kokoro model and current price](https://deepinfra.com/hexgrad/Kokoro-82M)
- [Kokoro model card and license](https://huggingface.co/hexgrad/Kokoro-82M)
- [Google Cloud TTS pricing](https://cloud.google.com/text-to-speech/pricing)
- [Deepgram pricing](https://deepgram.com/pricing)
- [ElevenLabs developer API offer](https://join.elevenlabs.io/api/developer-api)
- [ElevenLabs subscription pricing](https://elevenlabs.io/pricing)
