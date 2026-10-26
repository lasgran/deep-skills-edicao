---
name: remotion-short-video-editing
description: >-
  Use para editar Short/Reel/TikTok, explainer de ~2 min ou anúncio UGC com
  Remotion (narração, legenda por palavra, memes/SFX, música): "edita o Short",
  "Short de história com memes", vídeo do canal @Históriaem2Minutos / Junon.
  Para o Short do canal comece por historia-shorts-pipeline.
---
# Remotion short video editing

## Standard flow
1. **Script**: hook in 0–2 s → friction → twist/payoff → loop or CTA.
2. **Voice**: natural voice (ElevenLabs or a human recording) beats robotic TTS. If TTS, use a neural voice (e.g. edge-tts) and check its license. Trim long pauses; speed up at most ~1.10×. Recipe: see `elevenlabs-expressive-tts`.
3. **Word timestamps**: use the `whisper-captions` skill (`junon_legenda.py --roteiro ... --modo palavras --json`, int16, `--lang pt`). Never use `@remotion/whisper-webgpu` (needs GPU).
4. **Visuals**: public-domain/CC photos (Wikimedia), real well-known memes, or AI clips (consistent character + lip sync). Note every source in a SOURCES.md.
5. **Mix**: voice + music ducked under speech (default -18 dB; meme/drama -11 to -14 dB; recipe in `ffmpeg-video-pipeline`) + SFX aligned by their peak to the beat they punctuate → one `mix.wav` mastered to -14 LUFS with `ffmpeg-video-pipeline/scripts/master_audio.sh` (2 passes).
6. **Remotion only draws**: Python writes a `timeline.json` (scenes, caption chunks, zooms, memes); the Remotion composition reads it and plays the single `mix.wav`.
7. **Render**: flags in `remotion-render-cpu` (`--gl=swiftshader`, never swangle/angle without GPU); final encode profile in `ffmpeg-video-pipeline` (CRF, never two-pass); then a contact sheet for QC.
8. **Credits + publish** only after the owner's OK.

## Captions
- Chunk size, font and position: standard in `whisper-captions` (1–4 words, centre y≈0.646). Meme Shorts may use Montserrat 800/900 with the punchline word in yellow.
- Build chunks from word tokens, never by concatenating raw strings: a known bug glued words together ("TWOSOLDIERS"). Always join with spaces and spot-check frames.
- Meme style: caption only, highlight just the punchlines; avoid piling extra text and emoji.
- Paid ads: smaller captions, clean professional end card (button-style CTA), no emoji, no pointing-finger or YouTube-style effects.

## Meme history Short (~40-47 s): the proven recipe
Reference build: a ~47 s history Short, approved first try. Project layout: `audio/` (Python), `research/` (image search/download), `public/` (img, meme, sfx, vid, mix.wav), `src/` (one composition + timeline.json), `MEME_SOURCES.md`.
1. **Script** (~110 words, 8 short lines): absurd hook ("In 1932 X declared war... on birds. Yes. Birds."), fast facts with numbers, setup → failure beats ("Easy, right? No."), a real quote, a scoreboard punchline ("Final score: Emus 1, Australia 0"), CTA "follow the channel". Never change historical facts for a joke.
2. **Voice**: owner's ElevenLabs recording. Save the file immediately. Tighten pauses with an RMS silence detector (default gap ~0.22 s, but punchline words like "Birds.", "No.", "retreated." keep ~0.24-0.30 s), then speed up ≤1.10× with ffmpeg `atempo` (keeps the pitch).
3. **Align**: `whisper-captions` (`junon_legenda.py --roteiro ... --json`) → `palavras.json` (script text, Whisper times; no count matching needed).
4. **Meme gaps**: insert 1.3-1.9 s of silence into the voice at the joke beats (cut at the quietest point between the two words) and shift all word times after each gap. The meme plays inside the gap; others play ducked ~11 dB under the narration.
5. **Memes**: real, recognizable audio memes from myinstants.com, trimmed to the funny part, RMS-levelled (~-16/-17 dB): vine boom (hard zoom on a face), "Ah shit, here we go again", John Cena entrance, "Emotional damage", sad violin on a defeat. The matching meme image (imgflip template or a public-domain photo) shows only during its clip. Rotate memes across videos; never use meme jokes on real deaths/tragedies (e.g. Coffin Dance was vetoed for a plague).
6. **Images**: real period photos from Wikimedia Commons (search API → download → log in sources), shown with an "old" filter (grayscale/sepia/contrast), a slow Ken Burns move and a punch-in zoom plus a light exponential-decay shake on impacts.
7. **Mix**: voice + meme stem + SFX stem (whooshes on cuts, impacts on punch-ins) + a ducked thematic music bed (e.g. a military march) → stems kept separately → mix mastered to -14 LUFS. Python also writes the timeline (word times, scene starts, gaps, meme times).
8. **Remotion**: Montserrat 800/900 captions with outline, punchline word in yellow; Bangers only for rare meme labels; spring pop-ins; an end card with the channel CTA.
9. **QC**: contact sheet + frame checks (glued words, safe area, meme timing) before delivering.
Keep the structure (hook, quick story, meme punchlines, end card) but vary per video: visual style, hook type, music mood, memes and caption colours, so the Shorts don't all look the same.

## UGC ad with AI (25–30 s)
- Hook with before/after in the first 3 s, testimonial-style talking clips with consistent face and native lip sync, procedure shot, result, CTA to book.
- Pick licensed music for online ads, detect BPM, snap cuts to the beat grid.

## Formats
| Type | Resolution | fps |
|---|---|---|
| Short/Reels/TikTok/ad | 1080×1920 | 30 |
| YouTube explainer | 1920×1080 | 30 |

## Licenses
Prefer Mixkit, Kenney, Pixabay, CC0 Freesound for music/SFX; check commercial/ad use; keep a credits file. Meme clips are copyrighted short references (usual meme practice), not CC: log them separately.

## Before delivering
- Watch the contact sheet: glued words, captions off safe area, wrong meme timing, clipping audio.
- Confirm loudness (-14 LUFS) and file size fit the platform.
