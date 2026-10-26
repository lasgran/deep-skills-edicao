---
name: ai-character-consistency
description: >-
  Use this when the same stylized 3D characters (Pixar-like, e.g. fruit-people)
  must stay identical across 20-30 stills and video clips of a short vertical
  series: character bible, reference pack, prompt template, per-tool tactics
  (image edit, i2v, multi-reference r2v, lip-sync), continuity sheets, shot rules,
  QC and fixes in post.
---
# Keeping AI characters consistent across shots

Researched 2026-10-10. Related skills (don't repeat them): `grok-chat-consistent-stills` (one Grok chat per episode for stills) and `higgsfield-seedance-video` (API, prompt length, camera, 9:16). The core rule: **the reference set and the identity text are the lock.** No tool has a real "character lock" setting. Consistency comes from sending the same inputs every time and from shots designed so the models have little room to drift.

## 1. Character bible (one per character, frozen before shot 1)
Copy this block word for word into every prompt. Change it only on purpose and bump the version (v1, v2...).
```
ID: <NAME> v1  |  role: <one line>
Species/build: <fruit + body shape>, <height in heads, e.g. 3 heads tall>, <limb style: thin cartoon arms, 4-finger gloves>
Silhouette: <what reads in black fill: e.g. round body, leaf tuft tilted left, wide hips>
Skin/peel: base #RRGGBB, shadow #RRGGBB, highlight #RRGGBB  (name it too: "warm peach", NOT "orange")
Face: eye shape/color #RRGGBB, brows, nose, mouth at rest (closed smile / neutral)
Wardrobe: <item + color hex + material> (top / bottom / shoes); default state: hood DOWN, sleeves rolled
Signature props: <max 2, always in the same hand or place>
Render finish: "glossy stylized 3D animation, soft subsurface skin, Pixar-like, clean rounded forms"
Never: realistic skin pores, photoreal/game-engine look, <colors that belong to other characters>, extra fingers, logos/text
Differs from <SIMILAR CHARACTER>: <3 visible differences: color, silhouette, accessory>
```
- **Hex codes + a color word together.** Models don't read hex exactly, but the word ("pale peach") plus the hex keeps prompts identical and gives QC a target to check against.
- **"Never" list and "differs from":** they stop the redesign from sliding back toward a similar character or the reference series. Never name the inspiration series or its characters in prompts, and don't attach its images once the sheet exists.
- One **series style line** shared by every character (finish, lighting mood, lens). A character that comes out "realistic/game-like" almost always had a different or missing style line, or a photo-like reference.
- Max 3-5 anchors per character (color, silhouette, 1-2 props). Fewer, louder anchors survive better than long descriptions.

## 2. Reference pack (make once, approve, freeze)
1. **Hero anchor:** front, full body, neutral pose, arms slightly away from the body, plain light-grey background, even soft light, neutral expression. This is the only image made from text. Every other view is "anchor + one edit instruction" (pattern from shuohao-skills/character-refs), so if one view comes out bad you redo just that view.
2. **Head-and-shoulders portrait** from the anchor (faces hold best when a close-up is attached).
3. **Turnaround:** 90° profile and back, made from the anchor, not from each other.
4. **Expression sheet:** 4-6 heads (neutral, happy, surprised, sad, angry, talking-open), same light, same crop.
5. **Detail crops:** signature prop, hands (glove/finger count), any pattern or patch.
6. Save as `refs/<name>/v1/{anchor,portrait,profile,back,expr,details}.png` with `md5sum`s. A new anchor makes all its derived views stale.

Which image to attach for each tool:
| Tool / mode | Attach |
|---|---|
| Image edit (Manus/Higgsfield/Kontext-style) | previous approved still + portrait (+ anchor if it's a full-body shot) |
| Fresh still generation | anchor + portrait, + a style-key still from the same episode |
| i2v (Grok Imagine, Wan) | only the approved first frame. Identity lives in that frame |
| Seedance r2v (multi-ref) | per character: portrait + full-body anchor (2 images), then location. 4-5 refs total, most important first |
| Lip-sync (Wan + audio) | a first frame with the speaker big in frame and mouth closed or neutral |
Don't send full multi-view sheets to video models. ByteDance advises against multi-view sets of the same person (they cause averaging), and conflicting refs (lighting, costume, distance) blend into drift.

## 3. Prompt template
```
[IDENTITY: bible block(s), verbatim, for every character visible]
[STYLE: series style line, verbatim]
[SHOT: who does what (one action, with its end state), where, framing, one camera move, light source]
[CONTINUITY: from the scene sheet: hood down, wet fur, door open, prop in right hand]
[LOCKS: preserve identity exactly; only <X> changes; no text, no logo; mouth closed (if silent)]
```
- Name characters every time, never "she/he/they" once two are present. Give each character a tag and its own action ("A stays in the doorway; B lowers the bag").
- In edits, name what changes and what stays: "Change only the background to a kitchen; keep the same peach character, face, colors, pose and scale." Avoid "transform the character" (it re-casts the subject).
- For silent characters describe the state, not the negation: "keeps mouth closed, calm neutral expression". Don't keep repeating the word "talking".

## 4. Per-tool tactics
**Stills: edit the previous still or regenerate?** Edit when the new shot is the same scene, angle family and wardrobe state (change background, pose, expression, prop). Edits keep identity best when the change isn't to the character. Regenerate from anchor + portrait when the framing or location changes a lot, or after 3-5 chained edits (quality and identity fall off; Kontext authors show artifacts after ~6 turns). If drift appears, **go back to the last clean still**. Don't ask a degraded image to fix itself. Manus/Grok chat: keep one conversation per episode (see `grok-chat-consistent-stills`) but still re-paste the bible block.
**i2v first frame (Grok Imagine, Wan, Seedance i2v):** the still is the character. Prompt only motion + camera + "preserve the character and colors exactly". Re-describing the look adds drift. Start from a clean, well-lit frame at 9:16 with hands already in their final pose. Short clips (4-6 s) drift less. Generate 2-3 takes and keep the best. The Grok web UI can shift color/saturation per clip, so fix it in post (section 8) rather than re-rolling forever.
**Multi-reference r2v (Seedance 2.x):** give every image one role in the prompt ("@Image1 is Character A's face and colors; @Image2 is Character A's full body and outfit; @Image3 is the location"). Keep the same set, order and wording for every shot of the episode. More than 2 characters per clip = drift. For a known opening state, add the approved still as the first frame and use refs only for identity.
**Lip-sync (Wan 2.7 i2v + audio):** one speaker per clip, framed medium-close, locked camera, no hand-to-face. Audio must contain only that character's line (split dialogue per speaker; pad silences). Non-speakers: put them in separate shots, or generate without audio and prompt "mouth closed". If a mouth still moves, freeze-frame or re-sync to silence, or cut to a reaction shot. Kling and Seedance can also bind a voice to a character element, which is useful when a whole scene needs talking.
**Midjourney (if used):** V7 `--oref <anchor> --ow 100-400`, only one oref image. Lower `--ow` + over-describe traits for a style change. Pair with `--sref` of the series style key.

## 5. Continuity sheet (one per scene; fill before generating, update after approval)
```
Scene <n> | location | time of day | key light direction + color temp | weather
Per character: wardrobe state (hood up/down, sleeves, accessories) | wet/dry/dirty | injuries/marks
  | prop + hand (L/R) | screen side (L/R) + eyeline | emotional state at start/end
Set state: doors (open/closed), objects moved, lights on/off
Shot log: shot # | still file + md5 | clip file | model/seed | verdict | notes for next shot
```
Before each shot, copy the previous shot's end state into the CONTINUITY line. Mark state changes (hood goes up in shot 7) as their own beat, shown on screen, so the change is visible and justified.

## 6. Shot design rules that prevent drift
- **One character per shot** whenever the story allows. Use shot/reverse-shot instead of two-shots. Max 2 on screen, 3 tracked only as background silhouettes.
- **Avoid hands where you can:** no hugs, handshakes, finger counting, passing objects, typing. Frame chest-up, keep hands out of frame or resting, and put props on tables instead of in hands.
- **Ownership by costume, not by hand:** if "who opens the door" matters, show the opener's sleeve color/pattern entering frame, or show them in frame opening it, or cut from their face to the door already opening. Never a bare anonymous hand.
- No crowds behind the heroes. Simple, uncluttered backgrounds. Avoid mirrors and reflections.
- Each clip gets one action with a clear end state. Big moves (turning around, sitting, standing up) get their own shot.
- Front and 3/4 angles hold identity best. Profiles and backs only when the turnaround exists.
- Same lighting setup within a scene. Strong colored light shifts skin color, so state it in the sheet and grade it out later.

## 7. QC checklist (every still before animating, every clip before editing)
- **Contact sheet:** the sheet anchor next to every still/frame of the episode: `montage refs/A/v1/anchor.png shots/*.png -tile 8x -geometry 270x480+4+4 contact.jpg` (ImageMagick), or extract mid-frames from clips with `ffmpeg -ss 2 -i clip.mp4 -frames:v 1 f.png`. Look for silhouette, color, prop and finish mismatches.
- **Skin hex check:** sample a lit skin patch (cheek or forehead, avoid highlights) and compare it to the bible base hex in Lab (ΔE < ~8 ok, > 12 redo/grade):
  `python3 -c "from PIL import Image;im=Image.open('f.png').convert('RGB');x,y,r=540,700,6;px=[im.getpixel((i,j)) for i in range(x-r,x+r) for j in range(y-r,y+r)];print('#%02X%02X%02X'%tuple(sum(c[k] for c in px)//len(px) for k in range(3)))"`
- Finish: glossy stylized vs realistic/game look (pores, hard specular, photographic DOF). Redo if it doesn't match.
- Hands: finger count, glove style, no extra or orphan hands, the right character's sleeve.
- Wardrobe/props against the continuity sheet (hood, wet/dry, which hand).
- Mouths: only the speaker moves. Eyes don't change color mid-clip.
- No text/logos. Character not drifting toward the reference-series design (compare to the "differs from" list).
- Log the verdict in the shot log. Fix at the earliest stage (still before clip).

## 8. Fixes in post
- **Color match to reference:** match the clip's skin to the sheet. Shift chroma globally, leave brightness: measure skin Lab a/b, then `colorbalance`/`colortemperature`/`hue` in ffmpeg, or make a histogram-transfer `.cube` LUT from a clip frame to the approved still and apply `-vf lut3d=match.cube`. Match exposure (`eq`) first, then cast, then saturation. Check that faces sit on the vectorscope skin line. One LUT per scene, not per clip.
- **Crop/trim:** 9:16 delivery from a slightly wider frame lets you crop out a morphing hand or stray character. Trim the clip before the morph starts. Speed-ramp or hold the last clean frame (freeze 0.3-0.8 s) to cover it.
- **Reuse clean frames:** make a broken clip's best frame the new first frame and re-animate. Use clean reaction shots and cutaways (prop close-ups, environment) to cover cuts. A clip with bad lips becomes a reaction shot with the line played over another angle.
- **Local repaint:** fix one frame or still region (hood, sleeve color, extra hand) with an image editor and re-animate from it, rather than regenerating the whole shot.

## 9. Symptom → likely cause → fix
| Symptom | Cause | Fix |
|---|---|---|
| Redesign drifts toward the inspiration character | inspiration images/names still in the inputs; vague descriptors | remove them; add the "differs from" + "never" lines; regenerate the anchor, rebuild the pack |
| Skin shifts (peach ↔ orange) between i2v clips | per-clip color pipeline, warm lighting words | same light words every shot; hex/LAB check; scene LUT in post |
| One character looks realistic/game-like | missing style line, photo-like ref, different generator | same style line + style-key still attached; regenerate that character's still in the same tool as the others |
| Hands morph | hands acting in frame, small in frame, fast motion | reframe chest-up, props on surfaces, shorter clip, trim before the morph |
| Wrong character's hand appears | anonymous hand, two characters near the action | show the owner's sleeve or the owner in frame; one character per shot |
| Hood/wardrobe flips between shots | no continuity state in the prompt | scene sheet + CONTINUITY line copied from the previous shot's end state |
| Mouths move when silent | audio or "talking" words leak; i2v default lip motion | separate shots per speaker; "mouth closed, calm"; no audio for silent shots; freeze/cut |

## 10. Episode workflow (summary)
1. Bible + reference pack per character → approve the anchors (human check) → freeze v1.
2. Shot list designed with section 6's rules; continuity sheet per scene.
3. Stills: edit-chain within a scene, regenerate across scenes; QC (section 7) before any video.
4. Video: i2v from approved stills; r2v for shots that need new angles; lip-sync only for speaker shots.
5. QC contact sheet of clip frames → post fixes (section 8) → log everything in the shot log.

## 11. Advanced open-source options (when worth it)
| Option | What | Worth it when |
|---|---|---|
| Character LoRA (Flux/SDXL/Qwen; kohya, ai-toolkit) | train 15-40 curated images of the approved design | a series runs many episodes and the character is original. Strongest lock for stylized non-human designs. Needs a GPU and ~1-2 h. Make the training set from the reference pack plus approved stills |
| IP-Adapter (+ FaceID) | image prompt adapter in ComfyUI/diffusers | quick zero-training identity/style carry-over. Weaker on exact colors |
| PuLID / InstantID / PhotoMaker | face-ID embedding injection | human faces. Of little use for fruit-people (no human face for the face detector) |
| StoryDiffusion | consistent self-attention across a batch of 3-6+ prompts | storyboard batches on SD1.5/SDXL. Research-grade |
| ConsistI2V | first-frame attention + low-freq noise init for i2v | research reference. Explains why a clean first frame matters |
| ComfyUI VNCCS / fofr consistent-character | pose/outfit/expression sprite pipelines from one character | generating turnaround and expression sheets locally |
The hosted tools (Seedance/Kling refs, edit models) are enough for one 20-30-shot episode. Move to a LoRA when the same cast comes back every week, or when a non-human design keeps drifting despite the refs.
