---
name: thumbnail-titulo-pacote
description: >-
  Use when planning the packaging of a YouTube video (long-form or a clip):
  thumbnail brief, title options, the title/thumbnail information split, and A/B
  test concepts. Not for Shorts hooks/retention (use youtube-shorts-growth).
---
# Pacote de thumbnail e título

O clique se decide em menos de 1 s, e 70% ou mais das views vêm do celular. Título e thumbnail funcionam como UMA proposta.

## 1. Coletar
Qual é o payoff real do vídeo, o tom emocional, o momento mais visual, se tem rosto ou personagem, se é longo ou corte, e se o público chega pela busca ou pelo navegar.

## 2. Dividir a informação
- O título leva a palavra-chave e a promessa.
- A thumb leva a emoção, o objeto ou o resultado.
- Nunca repita texto entre os dois. Escreva essa divisão antes de criar.

## 3. Títulos (3 a 5)
- 40 a 60 caracteres, gancho nos primeiros ~45.
- Curiosidade + um substantivo concreto.
- Número específico quando o fato permitir. Nunca invente número.
- Sem CAPS LOCK, no máximo 1 emoji.
- Busca: comece pela frase exata da busca. Navegar: comece pela emoção.
- Marque o recomendado e diga o motivo.

## 4. Brief de thumb (2 a 3 conceitos para A/B)
Cada conceito: nome e ângulo; foco único (rosto com emoção forte ou objeto); texto de até 4 palavras e onde fica; 2 ou 3 cores, 30 a 40% de espaço negativo; composição; teste a 120 px (o que precisa ser legível).
Entre conceitos, mude UM elemento grande.

## 5. Especificação e teste
- 1280x720 mínimo (1920x1080 ideal), JPG/PNG até 2 MB.
- Test & Compare do YouTube: até 3 variantes, até 2 semanas, mede fatia de tempo de exibição. Não existe para Shorts.
- Prévia reduzida: `ffmpeg -i thumb.png -vf scale=168:-1 preview_small.png`.

## Regras
- Sem clickbait que o vídeo não cumpre: o primeiro frame e os primeiros 10 s confirmam a promessa.
- Nada de sangue, nudez ou texto vulgar.
- Entregue em bloco copiável e pergunte: aprovar ou ajustar?

Fontes (MIT): sergebulaev/youtube-skills, AgriciDaniel/claude-youtube, Jakeschincariol/youtube-agent-skill.
