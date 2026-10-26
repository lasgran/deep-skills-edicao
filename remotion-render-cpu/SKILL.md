---
name: remotion-render-cpu
description: >-
  Use ao renderizar Remotion sem GPU (box ou PC Junon): "renderiza o Short",
  "render no Junon", "Remotion lento/travando", "flags de render", vídeo do
  canal @Históriaem2Minutos / História em 2 Minutos. Complementa o plugin
  remotion-render com flags medidas (gl, concurrency, x264, cache, vídeo de
  fundo).
---
# Render Remotion na CPU — flags medidas (fonte única)

Base: estudo de 300 quadros 1080×1920@30 num box de 8 vCPU sem GPU (Remotion 4). Valores do Junon são estimativa a partir disso.

## Comando padrão
```bash
npx remotion render <Comp> out/mudo.mp4 \
  --gl=swiftshader \
  --concurrency=3 \
  --offthreadvideo-cache-size-in-bytes=536870912 \
  --x264-preset=veryfast --crf=18 --muted
```
Depois junte com o áudio masterizado e faça o encode final pela skill **ffmpeg-video-pipeline** (perfil final `faster CRF19 192k 48 kHz`). Se o Remotion gerar o arquivo final direto (sem passar no ffmpeg), use `--x264-preset=faster --crf=19 --audio-bitrate=192k` e masterize o `mix.wav` antes.

## Regras
- **`--gl=swiftshader`**. `swangle` é o mais lento sem GPU (+13%, +40% com CSS pesado); `angle` pode tentar usar a GPU com defeito do Junon. Não use nenhum dos dois.
- **`--concurrency`** = menor entre (núcleos físicos livres ÷ 2) e (RAM livre GB − 1) ÷ 0,5. **Junon: 3.** Acima de 4 não compensa (3→4 ≈ 0). Cada aba ~0,4 GB.
- **Cache do OffthreadVideo = 512 MB** (padrão chega a metade da RAM; 5,6 → 4,1 GB, mesmo tempo).
- `--x264-preset=veryfast` quando a saída é intermediária (−47% CPU no encoder).
- Vídeo de fundo: **`<Video>` de `@remotion/media`** no lugar de `<OffthreadVideo>` (−22% tempo, −33% RAM). Imagens são ~2,3x mais baratas que vídeo.
- Saída final: CRF (+ `-maxrate/-bufsize` se houver limite de tamanho), **nunca two-pass**.
- PNG só se precisar de transparência; camada de legenda transparente: VP9 alpha ou ProRes 4444 e compor no ffmpeg.
- Fontes fora do box: re-encode CFR 30 fps (receita na ffmpeg-video-pipeline).
- Estimativa total vs flags antigas (`swangle`, c=2): **~35–45% menos tempo**.

## Studio vs render direto
Bots renderizam **headless direto** (`npx remotion render`). Só abra `npx remotion studio` quando o humano pedir pra ver/ajustar ao vivo. O plugin oficial já está instalado (cache v4.0.533): não reinstalar `remotion-dev/skills`.

## QC
Contact sheet + ffprobe (receitas na ffmpeg-video-pipeline). Confira tempo/quadro no log: no box ~100–125 ms/quadro com c=3–6.
