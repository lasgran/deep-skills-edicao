---
name: whisper-captions
description: >-
  Use para transcrever e legendar áudio/vídeo em pt-BR (SRT, ASS, palavra a
  palavra, JSON pro Remotion) com faster-whisper na CPU: "legenda o vídeo",
  "legenda do Short do canal", "legendas do @Históriaem2Minutos / História em 2
  Minutos", "legenda no Junon", alinhar legenda ao roteiro, queimar legenda
  dourada, traduzir legenda mantendo tempos.
---
# Legendas pt-BR (faster-whisper + CTranslate2, CPU) — fonte única

Scripts na pasta da skill (`scripts/`, copie a pasta inteira junto pro Junon):
- `scripts/junon_legenda.py` — **padrão para o canal**: legenda com texto = roteiro, tempos do Whisper. Doc completa: `scripts/LEGENDA-README.md`.
- `scripts/tx.py` — transcrição simples (sem roteiro) → SRT/VTT/JSON.
- `scripts/avaliar.py`, `scripts/tests/`, `scripts/fontes/InterJunon-Bold.ttf` (OFL), `scripts/requirements.txt` (faster-whisper==1.2.1, numpy; ffmpeg+ffprobe com libass/libx264 no PATH).
Testado em 22/10/2026: faster-whisper 1.2.1, CTranslate2 4.8.2, modelo `small`. Short de 59 s produzido ponta a ponta com esta skill (150/150 palavras = roteiro).

## Regras duras
- **Sempre pt.** O `junon_legenda.py` já usa pt FIXO no código — **não tem flag `--lang`** (passar `--lang pt` dá erro). O `tx.py` (sem roteiro) aceita `--lang pt` e você DEVE passar: o auto-detect erra (já detectou inglês, `estudos/whisper/RAIOX.md` L34) e dá confiança baixa com música/efeitos (p=0,48–0,69).
- **`compute_type=int16`** (padrão dos dois scripts). `int8` dá saída **aleatória/vazia** nesta CPU (mesma chamada 3x: 51/77/77 palavras, 3 textos diferentes; int16: 3x idêntico). ~1,1–1,3 GB de pico. `float32` também estável (~2,2 GB).
- Máquina nova (Junon): `python scripts/junon_legenda.py audio.mp3 --autoteste --compute-type int16`. Só use int8 se o `--autoteste` passar **várias vezes** (ele roda 2x e pode passar por sorte — no box passou 1 vez apesar do bug). Na dúvida, int16.
- Modelo `small`. **Não use medium** (int16 = 3,6 GB de pico).
- `num_workers=1`, `condition_on_previous_text=False`, decode via ffmpeg→numpy (bug PyAV 19 `metadata_errors`) — os scripts já fazem.
- **Não use `@remotion/whisper-webgpu`** (plugin remotion-captions): exige GPU, não roda no box nem no Junon.

## Receitas
```bash
cd <pasta-da-skill>/scripts
# Canal (texto = roteiro; tags ElevenLabs [curious] etc. são removidas; pt fixo, SEM --lang)
python3 junon_legenda.py narracao.mp3 --roteiro roteiro.md                 # SRT 42 chars x 2 linhas, 1–6 s
python3 junon_legenda.py narracao.mp3 --roteiro roteiro.md --modo palavras --json   # Shorts 1–4 palavras + JSON
python3 junon_legenda.py video.mp4 --roteiro roteiro.md --modo ass --estilo palavra --max-palavras 4 # ASS dourado
python3 junon_legenda.py video.mp4 --roteiro roteiro.md --modo queimar --threads 2 --trecho 20,8  # teste 8 s
# Sem roteiro (aqui SIM usa --lang pt)
python3 tx.py video.mp4 --lang pt --fmt srt,vtt,json --words      # small, int16, beam 5, VAD
# Tradução com os mesmos tempos
python3 junon_legenda.py video.mp4 --roteiro r.md --exportar-linhas
python3 junon_legenda.py video.mp4 --roteiro r.md --traduzir en --tradutor arquivo:video.en.txt
# Testes (sem modelo, <1 s)
python3 -m unittest discover -s tests -v
```
O que o `junon_legenda.py` faz: VAD Silero corta em blocos de 6–24 s nas maiores pausas → transcrição por bloco (descarta segmentos ruins e loops) → casa roteiro×reconhecido (difflib + Needleman-Wunsch fuzzy + interpolação) → `model.align` forçado onde não bateu → +60 ms no início de cada palavra (`--ajuste-ms`) → quebra por programação dinâmica. Cache por sha256 em `<out>/.cache_legenda/`.
Medido (Short 64,9 s): 171/171 palavras = roteiro; erro de tempo média 48 ms, p90 104 ms; 16–26 s de CPU com 4–2 threads.

## Padrão do canal (único)
- **Shorts: blocos de 1–4 palavras** (`--max-palavras 4`); SRT longo: 42 chars × 2 linhas, 1–6 s.
- Estilo: Inter 800 (`fontes/InterJunon-Bold.ttf`), branco com contorno, destaque dourado `#F2C14E`, centro em y≈0,646 da altura (≈1240/1920, acima da UI do Shorts).
- Para o Remotion: use `nome.palavras.json` (palavra, início, fim) e monte os blocos a partir dos tokens, sempre juntando com espaço.

## Erros comuns
- `--lang` dá erro no junon_legenda.py → esse script é pt fixo, tire a flag (ela só vale no tx.py).
- Texto em inglês/sem sentido no tx.py → faltou `--lang pt`.
- Texto some/muda entre execuções → int8; volte pra int16.
- OOM → small int16, threads 2; nunca medium/batched.
- `task=translate` só vai pro inglês → use `--traduzir`.
