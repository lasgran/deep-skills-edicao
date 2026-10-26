---
name: remotion-motion-showreel
description: >-
  Use para motion graphics só em código no Remotion (showreel, promo, vinheta;
  "reel feito em código"). Use this when making a code-only motion-graphics
  video in Remotion (showreel, promo reel, portfolio/brand bumper, "made
  entirely in code" style like the viral X showreels): analysis, scene recipe,
  techniques, staged approval, render.
---
# Code-only motion showreel in Remotion

Goal: a 30-40 s reel (9:16 1080x1920, optionally 16:9) made 100% in code: no filming, only cut-out photos, screenshots, SVG logos and UI built in React. Cuts on the music beat, no narration.

## 1. Study the reference first
Download the reference and break it down scene by scene before writing anything: count the scenes (~17 scenes of ~2 s in a 35 s reel is typical), and note the palette, fonts, recurring HUD and every technique. Save the analysis in the project note.

## 2. Style recipe (what makes it look premium)
- **Fixed HUD** over everything: name, site, "SCENE 01 / NAME" label and a running timecode in monospace.
- **Palette**: dark (purple/blue) with neon accents (green, cyan, orange). Drop in 1-2 light scenes for contrast.
- **Fonts**: Inter (or similar) + a monospace font.
- **Motion**: `spring()` on everything, nothing linear. Hard cuts or glitch/wipe on the strong beat.
- **Technique menu**: CSS 3D (rotateX/Y, translateZ), phones/laptops in 3D with real videos inside (`<Video>` from `@remotion/media`, cheaper than `<OffthreadVideo>`), counters with `interpolate`, text word by word with a hand-drawn highlight or circle, particles, 3D bar charts, isometric stacks, node graphs, a fake cursor clicking UI, a mosaic of flying cards. Real 3D via `@remotion/three` when needed.
- **Audio**: royalty-free electronic track (Pixabay etc.), scene changes on the beat (pick the music and BPM BEFORE animating), SFX on every transition (whoosh, click, glitch), final mix at -14 LUFS.

## 3. Scene skeleton (~10 scenes, ~3 s each)
1. BOOT: an editor timeline assembling itself plus name and role.
2. WHO: big name plus avatar, rotating text rings.
3. PHRASE: light background, tagline word by word, key words circled.
4-7. WORK: one scene per highlight piece (3D phone spinning with the video, 2 phones side by side, phone plus label, mosaic of flying cards).
8. SITES: 3D laptop with a site scrolling, plus a phone.
9. SERVICES: list of services climbing in a staircase.
10. CTA: name, WhatsApp/contact, link, a short human sign-off.
No empty frames: every second needs something moving or entering (gaps at mid-reel are the classic v1 flaw). Corner/HUD text must stay legible on a phone.

## 4. Staged workflow (saves credits and rework)
1. Script + scene list for approval.
2. 3-scene preview (BOOT, the hardest 3D scene, CTA) with music, for approval.
3. Remaining scenes, music, SFX, full render.
4. Review frame by frame (gaps, text size, beat sync, SFX) before delivering, then rounds of fixes.
Typical effort: 2-3 h total.

## 5. Setup and render
- The official Remotion plugin skills are already installed (v4.0.533); don't reinstall. Study the templates in `remotion-dev/remotion` and `@remotion/three`.
- Put the assets (videos, cover images, site screenshots, logos, the reference video) in one project folder with a short note listing what is where.
- CPU-only machines: render flags in `remotion-render-cpu` (`--gl=swiftshader`; 3D/WebGL takes ~10-20 min per 30 s). Source videos Windows can't read: CFR 30 fps re-encode recipe in `ffmpeg-video-pipeline`.
