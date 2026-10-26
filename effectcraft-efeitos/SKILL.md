---
name: effectcraft-efeitos
description: >-
  Use para aplicar efeitos de motion/VFX (raio, flare, glitch, page turn, filme
  velho, neve, planeta, chroma key, voz de deus/vilão) em clipes de Shorts via
  EffectCraft headless na box (ec_apply.sh).
---
## Install (done on the box)
- EffectCraft v0.16.0 (MIT/Apache-2.0), prebuilt linux tarball from github.com/storytold/effectcraft/releases in /opt/effectcraft; `effectcraft-cli` in /usr/local/bin. Reinstall: download tarball + SHA256SUMS.txt, verify, copy to /opt/effectcraft, symlink the cli.
- Docs: docs/agents.md in the repo; `effectcraft-cli --help`; `effectcraft-cli exec effect.list --empty --json` (307 effects with param ids/defaults). Library and full list: /workspace/effectcraft_lib (README.md, effects.json).

## Wrapper (/workspace/effectcraft_lib)
    ./ec_apply.sh list
    ./ec_apply.sh <preset> <in.mp4> <out.mp4|out.wav> [param=value ...] [--in2 b.mp4] [--w 1080 --h 1920 --fps 30 --dur S] [--text "TITLE"] [--save p.ecproj]
- Input scaled to cover the comp (default 1080x1920@30), length = clip, audio kept.
- `param=value` -> effects/#1/<param> (JSON; points in comp pixels); full paths like `transform/opacity=50` or `effects/#2/amount=40` work.
- Transitions and keylight take --in2 (B clip / background); transition centred mid-clip.
- Re-render saved project: `effectcraft-cli render p.ecproj --comp Main --out o.mp4 --format h264`.

## Presets (purpose - key params)
- Looks: glow (threshold,radius,intensity), vignette, grain (subtle mono film grain), fractalnoise (smoke overlay), dustscratch (old film: sepia+grain+vignette+flicker), cartoon, brushstrokes, kaleida, mirror.
- Motion/punch: shake (wiggle), zoompunch, zoomblur, bulge, turbulent, wavewarp, echo (echoOperator=3 brighter), timewarp (speed).
- Light/energy: lightning (Thor bolt - origin,direction,glowColor), beam, lightburst, lensflare, lightsweep, lightrays, lightleak.
- Particles/weather/space: particles (embers), snow, rain, starburst (replaces image), sphere (rotating planet).
- Breakups/glitch: glitch, rgbsplit (VR Digital Glitch), shatter, burnfilm (keep 0-22, >30 = black), blockload, cardance.
- Transitions (--in2): flashdip, dipblack, strobe, pageturn (small artifact), lightwipe, cardwipe (looks like block wipe), irisswipe, jaws.
- Text: writeon (--text; brush max 50 px, keep text ~70 px).
- Keying: keylight (in = green screen, --in2 = background).
- Audio: godvoice (reverb+bass), villain (distortion+flange+bass). Listen before publishing.

## Raw CLI pattern
    effectcraft-cli run --empty comp.new '{"name":"Main","width":1080,"height":1920,"frameRate":30,"duration":3,"open":true}' file.import '{"paths":["/abs/in.mp4"],"addToComp":true}' layer.rename '{"layer":"#1","name":"Clip"}' effect.apply '{"layers":["Clip"],"effect":"Glow"}' prop.set '{"layer":"Clip","path":"effects/#1/radius","value":80}' --save-as p.ecproj
    effectcraft-cli render p.ecproj --comp Main --out o.mp4 --format h264 --audio auto
    effectcraft-cli render-frame p.ecproj --comp Main --time 1.5 --max-side 480 --out f.png

## Gotchas
- Alpha software: always verify renders by extracting frames.
- Absolute paths for file.import; new layers go on top (import B first, then A).
- Generators that replace the layer (Particle World, Star Burst, Sphere) go on a black solid in Add/Screen mode to keep the clip.
- CPU render ~5-35 s per 3 s 1080x1920 clip.
- Use effects with taste: one or two per moment, synced to the beat or punchline, never stacked everywhere.
