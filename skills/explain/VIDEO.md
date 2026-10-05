# Spoken explanations and video

Use the same writing rules for narration, captions, and on-screen text.
Create a video when the requested format or teaching goal warrants it. A short procedure can remain text.

## Write the script

- Aim for 12–15 words in each spoken sentence. Keep descriptive sentences below the 25-word limit.
- Use “you” when you address the viewer. Use a command for an action the viewer performs.
- Use “First,” “Now,” and “Next” when they help explain a sequence.
- State a needed caution before its action appears on screen.
- Use short noun phrases for callouts. Keep articles where they help identify the object. Avoid groups of more than three nouns.
- Open with the video's subject. Close with what the viewer now understands or can do.
- Keep captions faithful to the spoken script. Do not replace exact technical names with pronunciation spellings in captions.

## Build and check

Keep the source, script, scene audio, captions, and export in one project folder.
Use `output/video/<topic>/` unless the user specifies another location.
Save the script in `script.md` before synthesis.

Use local Kokoro and Remotion by default when they fit the requested language and available tools.
Initial package and model downloads need a network connection. Local synthesis needs no speech API key.
A zero API bill does not mean zero compute cost.
Do not switch to hosted speech without authorization.

Use the [editable video example](https://github.com/asunchu/explain/tree/main/examples/explain-video) as the existing template.
It includes pinned dependencies, a storyboard, narration scripts, a renderer, and verification commands.
The installed skill does not bundle that project's dependencies, model weights, or finished media.
Copy the source into the new project when useful. Replace its subject, script, and visuals before rendering.

Read [the animation guide](references/animation.md) for rendering choices and [the narration guide](references/tts.md) for speech setup.
Cache scene audio by script, model, voice, and voice settings.
Measure the audio before setting scene lengths. Drive motion from frames, not wall-clock time.
Render a representative segment before the full export.

Check the export's codecs, dimensions, frame rate, duration, and audio stream.
Decode the complete video. Inspect scene boundaries and dense frames.
Listen to pronunciations and the final sentence. Check captions against the actual speech.
Report any checks you cannot perform. Do not describe unplayed audio as auditioned.

Deliver the video, source, transcript, subtitle file, and reproduction command.
Keep output local unless the user authorizes publication.
