---
name: higgsfield-seedance-video
description: >-
  Use this when generating AI video clips with Higgsfield (Seedance 2.0/2.5,
  Kling, Genjutsu restyle/motion transfer/object swap): animating stills into
  B-roll, prompt writing, camera moves, 9:16 Shorts, the API flow and pitfalls.
---
# AI video with Higgsfield + Seedance (+ Genjutsu)

Researched 2026-10-08 from official Higgsfield docs and skills (github.com/higgsfield-ai/skills), OSideMedia/higgsfield-ai-prompt-skill, Emily2040/seedance-2.0, dexhunter/seedance2-skill and LearnPrompt/awesome-seedance. Full notes with sources: `/workspace/ai-video-skills/research.md`. Recheck prices and model names on the docs before relying on them.

## 1. Access (headless box)
- Use the Higgsfield REST API with a key from console.higgsfield.ai. Header: `Authorization: Key KEY_ID:KEY_SECRET`. Python SDK: `pip install higgsfield-client` (env `HF_KEY="id:secret"`). One key covers Seedance 2.0/2.5, Kling, Wan, Genjutsu, Grok Imagine Video and more.
- The official CLI and MCP use browser device-login/OAuth, so prefer the REST key on a server. Read `curl | sh` installers before running them.
- Jobs are async: submit, poll `status_url` (or a webhook), then **download right away** (outputs are kept at least 7 days).
- Inputs must be **public URLs** (no cookies). Host stills or clips somewhere public first.
- Run `POST https://api.higgsfield.ai/estimate/<endpoint>` before each batch. Failed or NSFW-blocked jobs aren't charged.
- Never use tools that ask for pasted browser session cookies or get past Cloudflare (for example Hikhakk/higgsfield-mcp-unified). Ignore unaffiliated "genjutsu-ai" SaaS sites.

## 2. Pick the tool
- **Still to motion (B-roll):** Seedance 2.5 image-to-video, `POST /bytedance/seedance-2.5/image-to-video`, 4–30 s, 480p/720p/1080p. Kling 3.0 is the alternative (it also takes an end frame).
- **Edit an existing clip with words:** Seedance 2.5 `video-edit` (output follows the source length).
- **Edit an existing clip with reference images:** Genjutsu.
  - `motion-transfer/v1.0`: carries the source clip's motion onto subjects from 1–8 reference images (for example, someone acting a meme gesture on a phone becomes an illustrated character).
  - `object-swap/v1.0`: replaces a character, outfit, object or location from 1–8 refs (source of at least 409,600 px per frame).
  - `restyle/v1.0`: needs a `preset_id` from `GET /models/higgsfield/genjutsu/restyle/v1.0/presets`, takes up to 5 character images, and keeps motion, composition and source audio. The prompt only says what to retain.
  - Source clip 4–30 s (longer is trimmed). Genjutsu does not animate stills. Blog price for 15 s: about 40 credits at 480p, 104 at 720p, 144 at 1080p.

## 3. Prompt rules (all models)
- Keep it short: about 40–110 words, under ~200 tokens. Long prompts distort.
- Order: Subject, Action, Camera, Look/Style (OSideMedia's "Model · Camera · Subject · Look · Action").
- **One camera move per shot.** Stacked moves jitter. Slow moves need distance plus time ("pulls back 10–15 cm over 7 s"). Reliable phrases: "locked-off static camera", "slow dolly push from medium shot to tight close-up over 8 seconds", "crane rising from ground level to overhead", "smooth 180-degree orbit at eye level".
- Camera vocabulary: Dolly In/Out, Dolly Zoom, Crane Up/Down, 360 Orbit, Arc, Crash Zoom, FPV Drone, Handheld, Whip Pan, Bullet Time, Dutch Angle, Overhead, Hyperlapse, Through Object. Through the API these work as prompt words, not presets.
- One primary action plus 1–2 secondary ones, one named light source and one named style.
- Phrase positively ("tack sharp", not "no blur"). Most models have no negative field. Use lock lines such as "no subtitles, no logo, no watermark".
- **Never generate on-screen text.** It comes out garbled. Add all titles, captions and memes in the editor.
- Describe only what is visible or audible. Show emotion as physics ("jaw clenches"), not "looks angry".
- Age-blind wording: describe by role and clothing, never boy, girl, child or young.

## 4. Image-to-video
- Prompt only what the still can't show, and add "preserve [identity/scene] exactly". Re-describing the frame causes drift.
- Template: `@Image1 is the first frame; preserve the subject and scene exactly. Only [motion] changes. Camera: [one move]. Lighting: [one source]. Constraint: no text, no logo.`
- **Hold mode** (paintings, maps, portraits): 3–4 small movements such as dust in light beams, smoke, a flag, a blink, with no camera move or one slow push-in.
- **React mode** (a character moment): split one emotion into beats and give the key beat at least 2 s.
- Fixes: identity drift, so describe less and lock more; camera jumps, so give one move with start and end; a static result, so add one physical action plus a time cue; background wobble, so animate only light or weather.
- **Action-reversal bug:** a short action finishes and then plays backwards to fill the clip. Chain 2–3 actions in one direction and name the camera's end point.
- Walking glides, so write "heel lands first, strict left-right alternation". Treat crowds as background and track at most 3 characters.

## 5. Multi-shot and timing
- Seedance 2.0: write "Shot 1 / Shot 2 / Shot 3" with the cut in words. Timestamps like "0–3 s" are unstable on 2.0.
- Seedance 2.5 accepts whole-second timestamps. Treat them as a budget and state the end state.
- For narrated videos, separate 5–8 s clips are easier to cut on the beat than one long multi-shot.

## 6. Vertical 9:16
- Image-to-video output follows the input image's framing, so **crop or outpaint the still to 9:16 first** (1080×1920). Text-to-video and reference-to-video take `aspect_ratio: "9:16"`.
- Keep the subject centered, avoid fast sideways action that leaves the frame, and leave the lower third clean for captions.
- Lock **one style-key image** and the same style sentence for every clip in a video.

## 7. Comedy and meme beats (LearnPrompt meme-comedy)
- Fix the punchline first and work backwards. Make the twist a visible object. Keep the camera and physics dead serious. Hold one silent second before the twist. Leave a clean tail frame for text added later.

## 8. Audio
- Seedance makes native audio. For narrated videos, generate ambient sound only (no speech) and mix narration and music in the editor.

## 9. Pipeline
1. Script and shot list: one beat per narration line (3–8 s). Research facts first and never invent quotes or dates.
2. Stills at 9:16 plus one style key. Paintings or photos of real people may trip Seedance's real-face filter, so test one early. The fallback is to stylize the still first, then animate.
3. Draft at 480p/720p, one camera move each, motion-only prompts. Show a preview before paying for 1080p finals.
4. Optional Genjutsu restyle or motion-transfer pass.
5. Download at once and log the prompt, model, credits and verdict for each take.
6. Assemble in the editor (for example Remotion `<OffthreadVideo>`), where all typography, captions and memes live. Review frames before delivering.
