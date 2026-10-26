---
name: narracao-recap-explainer
description: >-
  Use when narrating over existing footage or images (recap de filme/série,
  explainer de história ou espaço sobre B-roll): deciding per beat who owns the
  audio (fala original, som de ação, silêncio, música ou narração), giving each
  narration block one job, fitting text to the time window, and self-reviewing
  before TTS. Complements short-form-video-pipeline and
  remotion-short-video-editing.
---
# Narração recap / explainer por cima de imagem

Método de decisão do roteiro narrado: quando narrar, quando calar e quanto texto cabe.

## 0. Modo
- CRIAR: compare 2 estruturas (cronológica × começar pelo clímax) e registre por que uma perdeu.
- DIRIGIDO: execute fielmente o que o usuário definiu.
- REVISÃO: o feedback mais recente manda; o que não foi citado não muda.

## 1. Direção
Promessa, ponto de vista, pergunta dramática, emoção inicial e final, o que fica escondido e quando é revelado.

## 2. Beat = mudança
Cada beat muda conhecimento, poder, objetivo, relação, emoção ou risco; se sai e nada se perde, sai. Entre tarde e saia cedo, preservando fala inteira, gesto e pausa. Corte em fim de frase, nunca no meio da palavra; evite cortar a poucos frames de um corte original.

## 3. Dono do som
Para cada beat, `audio_owner`: fala_original | som_de_acao | ambiente/musica | silencio | narracao. Se narração, UM trabalho: contexto, elo_causal, prenuncio, interpretacao, transicao, ou nenhum (não tape a imagem). 70/30 narração/original é só ponto de partida. O bloco antes de uma fala original deixa vontade de ouvi-la; o seguinte retoma o que ela causou.
```json
{"beat":"b03","muda":"poder: A→B","momento":"reação após a recusa","audio_owner":"fala_original","trabalho_da_narracao":"nenhum"}
```

## 4. Caber no tempo (antes do TTS)
- Meça a velocidade da voz; cada bloco custa ~0,45 s extra de silêncio do TTS.
- Janela de 2-3 s: 1-2 palavras a menos do que a conta. Nunca acelere a voz.
- Texto acima de 1,25x o orçamento: reescreva.
- Blocos a menos de ~1,6 s formam parágrafo, com ~0,35 s de pausa.
- Ducking em 2 níveis (forte sobre fala original, leve sobre ambiente).

## 5. Escrever para o ouvido
Primeiro o trabalho, depois a frase. Um pensamento por bloco, numa chamada de TTS. Não descreva o que a imagem mostra. Nomes próprios em vez de ele/ela. Verbos concretos. "Não é A, é B" só se o público acreditaria em A. Não picote a narração para caber na legenda.

## 6. Autorrevisão contrafactual
Apague cada beat; troque quem fala por quem reage; teste sem som; teste só áudio; troque narração por fala original ou silêncio; a pergunta da abertura é respondida? Corrija os 1-3 problemas de maior retorno.

## 7. Fatos (opcional)
Peça a um revisor: alguma frase afirma algo que imagem, fala ou pesquisa não sustentam? Alucinação é erro.

## 8. Referência (opcional)
Meça cortes/min, proporção narração × original × silêncio, palavras/s e quando aparece a 1ª fala original. Guarde só método e números.

Fonte (MIT): zenstory-ai/video-recap-skills.
