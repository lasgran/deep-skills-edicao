---
name: elevenlabs-expressive-tts
description: >-
  Use this when writing ElevenLabs text-to-speech scripts (Eleven v4/v3 audio
  tags, pauses, emphasis, settings) for narration or character lines, including
  Brazilian Portuguese.
---
# Expressive ElevenLabs TTS (v4, v3, Multilingual v2)

Researched 2026-10-09 from official ElevenLabs docs and github.com/elevenlabs/skills. Notes with sources: `/workspace/ai-video-skills/elevenlabs-research.md`. Models change over time; re-test prompts now and then.

## Models
- **eleven_v4 / eleven_v4_turbo** (released 2026-09-28): the default for expressive work. Only two settings, Stability and Similarity (no Style or Speed slider, no SSML). Supports Brazilian Portuguese (`language_code: "pt"`). It can also generate sound effects, so a tag describing a noise may come out as a noise.
- **eleven_v3:** same tag syntax as v4, less reliable.
- **eleven_multilingual_v2:** no audio tags (remove them), supports `<break time="x.xs"/>` up to 3 s, has Style, Speed (0.7 to 1.2) and speaker boost.

## Writing for v4/v3
- Tags are short English instructions in square brackets, placed right before or after the words they affect. Use 1 to 3 per line; overuse makes the read unstable.
- Emotion and delivery: [sarcastic] [curious] [excited] [mischievously] [dismissive] [deadpan] [angry] [annoyed] [appalled] [thoughtful] [surprised] [dramatically] [whispers] [shouts]. Free descriptions also work: [Low, steady voice, restrained urgency].
- Reactions: [laughs] [chuckles] [soft chuckle] [sighs] [exhales sharply] [inhales deeply] [clears throat] [snorts].
- Pacing: [short pause] [long pause], ellipses and dashes. `<break>` does NOT work on v4/v3.
- Emphasis: CAPS on one key word, plus ! and ?.
- Accent: [strong French accent] etc. (experimental). A voice cloned in another language speaks pt-BR without the original accent unless told.
- Keep spoken text in Portuguese and tags in English (all official examples use English tags).
- Only describe sounds the voice makes; never stage directions like "he said angrily" (older models read them aloud).
- Write numbers and units out in words.

## Settings (starting points)
- Character or comedy line: stability 0.3 to 0.4, similarity 0.75 to 0.8.
- Calm narration: stability about 0.7, similarity about 0.5 (official skills repo); defaults are 0.5 / 0.75.
- Flat read: lower stability. Artifacts: lower similarity. Clean source audio matters (v4 copies noise and plosives).
- v2: stability 0.35 to 0.45, similarity 0.75, style 0.2 to 0.35, speaker boost on, speed 0.95 to 1.0.

## Workflow
1. Write the line, fix the emotional arc (setup, pause, punchline) and keep facts unchanged.
2. Make 3 to 6 takes per short line (short lines vary a lot); reuse a good one with `seed`.
3. Save the chosen audio right away in the project folder.
4. Caption timing near tags can drift, so align captions to the real audio (word timestamps), not the script.

## Avoid
- Tags on v2 or Flash (no effect or read aloud).
- Old guides recommending `<break>` on v3/v4.
- Third-party proxies or CLIs that want your API key; use the official API or app.
