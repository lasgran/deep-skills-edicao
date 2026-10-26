---
name: ffmpeg-video-pipeline
description: >-
  Use para editar, converter, cortar, legendar, escalar pra 9:16, mixar
  voz+música e exportar vídeo com ffmpeg na CPU: "exporta o Short", "encode
  final", "preview", "masteriza o áudio -14 LUFS", "Short do canal /
  @Históriaem2Minutos / História em 2 Minutos", "renderiza no Junon". Perfis de
  entrega medidos com VMAF.
---
# ffmpeg — pipeline de vídeo (fonte única de encode, loudness e mix)

Testado: ffmpeg `7.1.5-0+deb13u1` (box Linux), **CPU only** (`libx264` + `aac`). Sem GPU (nvenc/amf/qsv não testados; o Junon tem GPU com defeito). Antes de flag rara: `ffmpeg -hide_banner -encoders|-filters | grep -w NOME`.
Scripts na pasta da skill: `scripts/master_audio.sh` (loudness 2 passadas) e `scripts/smoke.sh` (valida todas as receitas; trabalha em /tmp/ffsmoke). Rodar `bash scripts/smoke.sh` em máquina nova → esperado `pass=11 fail=0`.

## Perfis de entrega (medidos com VMAF, fonte única — não improvisar)
| Uso | Flags |
|---|---|
| **Final/upload (Shorts 1080×1920)** | `-c:v libx264 -preset faster -crf 19 -pix_fmt yuv420p -c:a aac -b:a 192k -ar 48000 -movflags +faststart` (VMAF 97,5–97,7 = medium/slow, −35% CPU vs medium) |
| **Preview/rascunho** | `-vf scale=540:960 -c:v libx264 -preset ultrafast -crf 26 -pix_fmt yuv420p -c:a aac -b:a 128k -movflags +faststart` (mais nítido que veryfast CRF28) |
| **Junon com PC ocupado** | `-threads 2` antes de cada `-i`; `-preset faster -crf 20 -threads 4`; prioridade baixa (`nice -n 10` / BELOW_NORMAL) |
| **Limite de tamanho (envio por chat)** | 1 passada: `-preset faster -crf 21 -maxrate 6M -bufsize 12M`; se 18 MB/60 s obrigatório: `-preset medium -crf 23 -maxrate 3600k -bufsize 7200k`. **Não usar 2 passadas** (mesma qualidade, +30% CPU) |
Não use: `slow` (+73% CPU p/ +0,1 VMAF), CRF 17 (arquivo 2x sem ganho), `tune=film/grain`. `tune=animation` só pra motion graphics.

## Loudness (-14 LUFS, true peak -2,5 dBTP) — 2 passadas
```bash
bash scripts/master_audio.sh mix.wav master.wav        # [-14] [-2.5]
```
Faz: loudnorm análise → loudnorm `linear=true` com os valores medidos → mede de novo e corrige se |erro|>0,3 dB → `alimiter` com oversampling 192 kHz → 48 kHz. Medido: -14,1 LUFS, pico -2,5. **Nunca loudnorm de 1 passada** (pode cair no modo dinâmico). Rode o áudio em paralelo com o vídeo.

## Mix voz + música + SFX
- `amix ... normalize=0` e controle com `volume=`. Música padrão **-18 dB sob a fala** (`volume=0.125`); exceção: dramas/meme podem usar -11 a -14 dB. Masterize depois com `master_audio.sh`.
```bash
ffmpeg -i voz.wav -i musica.wav -i sfx.wav -filter_complex "[1:a]volume=0.125[m];[0:a][m][2:a]amix=inputs=3:duration=first:normalize=0[a]" -map "[a]" -c:a pcm_s16le mix.wav
```

## Regras
- Sempre `-hide_banner -y`; em scripts `-loglevel error`.
- Grafos com muitos inputs: **`-threads 2` antes de cada `-i`** (RAM 7,0 → 4,75 GB medido).
- `perspective` e filtros caros sempre com `enable='between(t,a,b)'`; evitar `zoompan`; overlay da legenda só na faixa dela.
- Fundo desfocado: blur em 1/4 da resolução (`scale=270:480,boxblur=6:2,scale=1080:1920`), não `gblur σ30` em 1080p.
- `scale=-2:H` (largura par). `-c copy` corta só em keyframe; corte preciso = reencode.
- Opções modernas: `-fps_mode`, `-/filter_complex arquivo.txt`, `-q:v`.
- Validar: `ffprobe -v error -show_entries stream=codec_name,width,height -show_entries format=duration -of compact FILE` e `ffmpeg -v error -i FILE -f null -`.

## Receitas
```bash
# Shorts 9:16 crop central (final)
ffmpeg -i in.mp4 -vf "crop=ih*9/16:ih,scale=1080:1920,setsar=1" -c:v libx264 -preset faster -crf 19 -pix_fmt yuv420p -c:a aac -b:a 192k -ar 48000 -movflags +faststart short.mp4
# Shorts 9:16 com fundo desfocado barato
ffmpeg -i in.mp4 -filter_complex "[0:v]split[a][b];[a]scale=270:480:force_original_aspect_ratio=increase,crop=270:480,boxblur=6:2,scale=1080:1920[bg];[b]scale=1080:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[v]" -map "[v]" -map 0:a -c:v libx264 -preset faster -crf 19 -pix_fmt yuv420p -c:a aac -b:a 192k -ar 48000 -movflags +faststart short_blur.mp4
# Juntar vídeo mudo + áudio masterizado
ffmpeg -i mudo.mp4 -i master.wav -map 0:v -map 1:a -c:v libx264 -preset faster -crf 19 -pix_fmt yuv420p -c:a aac -b:a 192k -ar 48000 -shortest -movflags +faststart final.mp4
# Legenda queimada: estilo do canal vem do ASS do whisper-captions (junon_legenda.py --modo ass)
ffmpeg -i in.mp4 -vf "ass=legenda.palavra.ass:fontsdir=<skill whisper-captions>/scripts/fontes" -c:v libx264 -preset faster -crf 19 -pix_fmt yuv420p -c:a copy burn.mp4
# Legenda soft
ffmpeg -i in.mp4 -i subs.srt -map 0 -map 1 -c copy -c:s mov_text -metadata:s:s:0 language=por soft.mp4
# Fonte de vídeo ruim pro Remotion/Windows: CFR 30 fps
ffmpeg -i src.mp4 -c:v libx264 -preset faster -crf 18 -bf 0 -g 10 -r 30 -an -movflags +faststart src30.mp4
# Corte preciso / thumbnail / contact sheet (QC)
ffmpeg -ss 1 -i in.mp4 -t 2 -c:v libx264 -preset faster -crf 19 -c:a aac cut.mp4
ffmpeg -ss 2 -i in.mp4 -frames:v 1 -q:v 2 thumb.jpg
ffmpeg -i final.mp4 -vf "fps=1/3,scale=270:-2,tile=6x4" -frames:v 1 contact.jpg
```
Medir loudness: `ffmpeg -i X -af ebur128=peak=true -f null - 2>&1 | grep -E '^ +(I|Peak):'`.

## Erros comuns
- `Cannot load libcuda.so.1` → sem GPU, use libx264.
- `width not divisible by 2` → `-2` no scale.
- Legenda sem acento → UTF-8 + `fontsdir` com a fonte.
