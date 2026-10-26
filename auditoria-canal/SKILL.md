---
name: auditoria-canal
description: >-
  Use when doing a periodic (monthly) YouTube channel audit or when asked "por
  que meu canal não cresce", "audita meu canal": reads the last titles as a set,
  tests thumbnails at feed size, scores the first 15 s of recent videos, checks
  upload consistency and retention, and ends in ONE fix for the week, three
  things to keep, and one thing not to do yet.
---
# Auditoria mensal de canal: termina em UMA correção

## Regras
- Nunca invente número; sem dado, diga e peça.
- Compare o canal com ele mesmo antes de benchmarks externos.
- Uma auditoria por canal; não misture Shorts com longos.

## Coleta
- Últimos 10 longos e 10 Shorts: `yt-dlp --flat-playlist --print "%(upload_date)s|%(duration)s|%(view_count)s|%(title)s" URL`.
- Thumbs: `yt-dlp --write-thumbnail --skip-download`.
- Transcrição dos primeiros 15-30 s dos 3 mais recentes.
- Studio, se houver: CTR, % assistido, tráfego, retenção.
- A auditoria anterior: a correção foi feita? funcionou?

## Ordem (pare no primeiro problema grave)
1. Os últimos 10 títulos como conjunto: específicos? variados?
2. Thumbs a ~160 px (`ffmpeg -i t.jpg -vf scale=160:-1 p.png`) em grade; 3+ ilegíveis = essa é a correção.
3. Primeiros 15 s dos 3 mais recentes: a 1ª frase confirma o título? pontuar o gancho (especificidade, endereçamento, stakes, curiosidade, brevidade; 60% média + 40% pior).
4. Constância de postagem (intervalos e desvio), não frequência.
5. Retenção: vazamento do gancho, quedas bruscas, declive.
6. Outliers do próprio canal (views ÷ mediana ≥3x): o que têm de diferente? Muitas vezes a correção é fazer mais disso.

## Escolher a correção
Siga o funil (clique → primeiros 15 s → meio). Escolha o problema mais cedo no funil, com evidência e executável esta semana. Escreva como ação concreta, não diagnóstico.

## Entregar
```
## Auditoria <canal> — <mês/ano>
**A correção:** <ação + como medir>
**Evidência:** <2-3 fatos com números reais>
**3 coisas que funcionam (não mexa):** 1. 2. 3.
**O que NÃO fazer ainda:** <tentação e porquê>
**Métrica para a próxima auditoria:** <uma, com valor atual>
```
Última linha: "publicar assim ou mudar?"

## Rotina
Mesmo dia todo mês; guarde cada auditoria. Mantenha a correção 1 mês (ou 3-4 vídeos) antes de trocar.

Fontes (MIT): Jakeschincariol/youtube-agent-skill (yt-audit), AgriciDaniel/claude-youtube (audit.md).
