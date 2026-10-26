---
name: sfx-sound-design-pass
description: >-
  Use when adding sound effects and music to a narrated short or video:
  proposing SFX cues synced to word timings and visual beats, building a
  reusable SFX library, writing an sfx-plan.json for approval, and mixing with
  voice ducking via ffmpeg.
---
# Passe de sound design (SFX + música)

A voz é o show. O SFX é tempero: sentido, sem cobrir a voz.

## Entradas
- Tempo de cada palavra (TTS ou whisper).
- Beats visuais em segundos calculados do código: `(frame_local + from) / fps`. Não chute.
- Tom da marca (épico, documental, suspense).

## Biblioteca reutilizável (`sfx/catalog.json`)
- Cada entrada: id genérico, tags, origem, licença, loudness, `used_in`.
- Reutilize antes de gerar; se faltar, gere ou baixe de fonte CC0/licenciada.
- Normalize em ~−20 LUFS, pico −1,5 dBFS.

## sfx-plan.json (fonte da verdade)
```json
{"master":"out/video-voiced.mp4","events":[
 {"at_s":4.90,"sfx_id":"whoosh-soft","gain_db":-3,"cue":"corte p/ cena 2"},
 {"at_s":13.03,"sfx_id":"impact-low","gain_db":0,"cue":"palavra 'explodiu'"}],
 "music":{"file":"music/bed.mp3","gain_db":-18,"duck":true}}
```

## Calibração inicial
- Transições/whooshes: −3 dB
- Impactos/pops: 0 a +3 dB
- Stamps/snaps: 0 a +7 dB
- Risers: 0 a +2 dB
- Clipes percussivos curtos soam 3 a 5 dB mais baixos após normalização: compense.
- Cue sob fala contínua some: coloque nas pausas.
- Textura ruidosa não se resolve com ganho: troque o som.
- Música: −18 a −24 dB sob a voz, com sidechain.

## Mixagem (ffmpeg)
`adelay` em cada SFX, `amix=normalize=0`, ducking da música com `sidechaincompress` usando a voz como chave, depois `loudnorm` final: −14 LUFS, true peak −1 dBTP. Meça transientes em janelas de ~0,3 s.

## Princípios
- SFX só em transições e revelações; camadas (riser → impacto) só em 2 ou 3 momentos-chave.
- Escolha cada som pela função (movimento, tensão, ênfase).
- Sincronize com frame e palavra: 100 ms de erro já parece desleixo.
- Revise a lista de cues antes de mixar e salve sons novos na biblioteca.

Fonte (MIT): hassancs91/claude-faceless-shorts-creator (suggest-sfx).
