---
name: historia-shorts-pipeline
description: >-
  Comece aqui para qualquer Short do canal @Históriaem2Minutos (História em 2
  Minutos): "faz o Short do canal", "vídeo de história", "Short sobre <fato
  histórico>", "E se...", "monta/edita/renderiza o vídeo no Junon". Ordem das
  etapas pt-BR e qual skill é dona de cada receita.
---
# Pipeline do Short de história (@Históriaem2Minutos) — roteador

Regra do Jun: **QUALIDADE > velocidade. Nunca entregar sem verificar (QC abaixo).** Esta skill só ordena e aponta; as receitas técnicas vivem nas skills donas.

## Formato
- 1080×1920, 30 fps, pt-BR. YouTube: **45–60 s** (mediana dos virais 57,5 s; roteiro ~140–150 palavras a ~2,6–2,9 palavras/s). Versão TikTok estendida 62–90 s quando fizer sentido.
- Visual muda a cada **2–4 s**; toda imagem parada recebe Ken Burns (zoom/pan lento). Nunca tela estática.
- Hook nos **0–2 s** (definido só aqui): pergunta absurda/"E se...", número forte ou contradição.

## Etapas e donos
| # | Etapa | Skill dona |
|---|---|---|
| 1 | Roteiro: hook → fatos curtos com números → virada → payoff → CTA "segue o canal". Nunca alterar fato histórico por piada. Fontes anotadas em SOURCES.md | `storytelling-serial-shorts` |
| 2 | Voz (ElevenLabs; tags, pausas, atempo ≤1,10×) | `elevenlabs-expressive-tts` |
| 3 | Legenda alinhada ao roteiro (int16, `--lang pt`, blocos 1–4 palavras, `palavras.json`) | `whisper-captions` |
| 4 | Imagens: Wikimedia Commons / domínio público; personagens IA consistentes | `ai-character-consistency`, `grok-chat-consistent-stills`, `higgsfield-seedance-video` |
| 5 | Mix voz + música (-18 dB sob a fala) + SFX → master -14 LUFS 2 passadas | `ffmpeg-video-pipeline` |
| 6 | Composição (timeline.json → Remotion só desenha) | `remotion-short-video-editing` |
| 7 | Render CPU (swiftshader, c=3, cache 512 MB) | `remotion-render-cpu` |
| 8 | Encode final `faster CRF19 192k 48k` / preview `ultrafast CRF26 540p` | `ffmpeg-video-pipeline` |

## QC obrigatório antes de entregar
1. Contact sheet (1 quadro/3 s): palavras coladas, legenda fora da área segura, quadro vazio/estático >4 s.
2. Loudness: I = -14 ±0,5 LUFS, pico ≤ -2 dBTP (`ebur128=peak=true`).
3. Legenda = roteiro (sem palavra trocada); timing spot-check em 3 pontos.
4. `ffprobe`: 1080×1920, 30 fps, h264 + aac 48 kHz; `ffmpeg -v error -f null` sem erro.
5. Duração dentro do alvo; créditos/fontes registrados.
Publicar só com OK do dono.
