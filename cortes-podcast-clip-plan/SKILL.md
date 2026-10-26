---
name: cortes-podcast-clip-plan
description: >-
  Use when turning a long video (podcast, interview, live, lecture) plus its
  captions into a ranked plan of vertical clips (cortes) with exact timestamps,
  hook line, cold open and metadata, e.g. for clipping contests. Plans only;
  cutting is done with the ffmpeg/Remotion skills.
---
# Plano de cortes de vídeo longo

Esta skill escolhe os trechos e escreve os metadados. O corte fica com ffmpeg-video-pipeline e remotion-short-video-editing. Nada é publicado.

## Entradas
Vídeo + legenda com tempo por palavra (gere com whisper-captions se faltar). Leia as regras do concurso: duração, marca d'água, hashtags, proibições.

## Passos
1. Conferir a sincronia: duração do vídeo vs tempo da última palavra (`ffprobe`). Se não baterem, pare. Nunca chute offset.
2. Ler a transcrição inteira antes de escolher. Picos de volume só confirmam.
3. Candidatos que se sustentam sozinhos: opinião forte, história com virada, número surpreendente, conflito, pergunta e resposta curtas, frase citável.
4. Para cada corte: `start`/`end` (HH:MM:SS.mmm, 15 a 30 s; limite 12 a 55 s ou o do concurso); `hook_line` com palavras EXATAS nos primeiros 1 a 2 s; motivo; nota 1 a 10; o que mostrar na tela. Corte respiração e "então…" do começo; termine na punchline, nunca no meio da frase. Se o começo depende de contexto, escreva um texto de gancho novo na tela.
5. Ranquear 5 a 8 cortes e escolher um cold open de até 10 s.
6. Metadados: título, descrição, hashtags. Números ditos são citação, não fato verificado.
7. Prévias: `ffmpeg -ss START -to END -i in.mp4 -vf scale=-2:480 -c:v libx264 -preset veryfast prev_N.mp4`; entregar `clip_plan.json` + tabela.

## Regras
- Sem timestamp e citação, não vira corte.
- Nunca sobrescreva originais.
- Corte só material autorizado.

Fonte (MIT): itsryanlenk/cutlist.
