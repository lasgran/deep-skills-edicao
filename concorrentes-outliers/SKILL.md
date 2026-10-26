---
name: concorrentes-outliers
description: >-
  Use when researching competitor channels or a niche on YouTube/TikTok/Reels:
  finding outlier videos versus each channel's own baseline, extracting
  repeatable hooks/formats/topics into a swipe file, spotting content gaps and
  trends, and mining comments for unmet demand.
---
# Concorrentes e outliers

O objetivo não é ordenar por views: é achar o que performou ACIMA do normal daquele canal e explicar o padrão repetível.

## 1. Escopo
- 3 a 5 canais concorrentes e a plataforma de cada.
- Janela: últimos 60 a 90 dias ou 50 vídeos mais recentes.
- Formato: Shorts/Reels ou longo. Nunca misture na mesma base.

## 2. Coletar dados públicos
- YouTube: `yt-dlp --flat-playlist -J "URL/shorts"` (ou `/videos`); detalhes com `yt-dlp -J URL` só quando precisar.
- TikTok/Instagram: `yt-dlp` no perfil quando funcionar; senão a página pública.
- CSV com URL, data, título, views, likes, comentários, duração.

## 3. Outliers
- `score = views / mediana(views do canal na janela)`.
- Outlier ≥ 3; superoutlier ≥ 10.
- Desconte vídeos com menos de 7 dias.
- Nunca compare views brutas entre canais grandes e pequenos.

## 4. Explicar cada outlier
Transcreva os primeiros 3 a 5 s (whisper-captions) e anote tipo de gancho, tema, formato, duração, estilo de título/thumb e ritmo. Separe padrão de sorte.

## 5. Lacunas e tendências
- Comentários pedindo temas e perguntas sem resposta.
- Google Trends e vídeos recentes de canais pequenos estourando.
- Ganchos de calendário: datas, estreias, aniversários históricos.

## 6. Entregar
Tabela de outliers com links; swipe file de 10 ganchos/formatos reescritos com ideias próprias (nunca copiar roteiro); 5 ideias priorizadas; 1 aposta da semana. Fonte e data de cada número.

## Regras
- Só dados públicos, respeitando os termos.
- Não invente métricas; diga o que falta.

Fontes (MIT): ScrapeCreators/social-media-research-skills, AgriciDaniel/claude-youtube.
