# junon_legenda.py: legendas pt-BR para os canais e para o Junon

Um arquivo Python só (`junon_legenda.py`, cerca de 1.150 linhas, resto em stdlib) que gera:
- **SRT no estilo do canal**: até 42 caracteres por linha, no máximo 2 linhas, de 1 a 6 s por legenda, com quebra na pontuação e espaçamento corrigido;
- **SRT palavra a palavra** (blocos de 1 a 4 palavras, como nos Shorts);
- **ASS** com destaque dourado (`karaoke` com `\k`, `palavra` só com a palavra atual, ou `canal`, sem destaque);
- **vídeo com a legenda queimada** (ffmpeg + libass), com pouca carga na máquina;
- **tradução linha a linha** mantendo os tempos, por um hook plugável.

O motor é o faster-whisper `small` com `language="pt"` sempre. **Com roteiro, o texto da legenda é o roteiro** (as tags do ElevenLabs, como `[curious]` e `[whispers]`, são removidas) e o Whisper só fornece os tempos.

## Como funciona
1. O ffmpeg decodifica para PCM 16 kHz mono direto num `numpy`. Isso contorna o bug do `decode_audio` do faster-whisper com PyAV 19 (`metadata_errors`).
2. O **Silero VAD** acha as pausas. O áudio é cortado **nas maiores pausas** em blocos de 6 a 24 s. Em janelas de 30 s, o `small` às vezes "pula" trechos inteiros.
3. Cada bloco é transcrito com `word_timestamps=True`, `vad_filter` (já feito no passo 2), `condition_on_previous_text=False`, `num_workers=1`, sem batched. Os segmentos ruins são descartados (temperatura alta, logprob < -1 ou compressão > 2,4). Repetições em loop ("a massa é a mesma, a massa é a mesma") são removidas. Se um bloco vier com menos de 1,3 palavra por segundo de fala, ele é **dividido e refeito**.
4. **Com roteiro**:
   - (a) as palavras do roteiro são casadas com as reconhecidas: âncoras exatas via `difflib`, trechos divergentes via Needleman-Wunsch com similaridade fuzzy (aceita 1:2 e 2:1, como "guiam" ≈ "segui am") e, o que sobrar, por interpolação proporcional às letras;
   - (b) **alinhamento forçado**: nos blocos onde alguma palavra não bateu exato, o próprio Whisper alinha o **texto do roteiro** ao áudio (`model.align`, cross-attention + DTW). Com `--forcado sim`, faz isso em todos os blocos.
5. As bordas das palavras são encaixadas na fala detectada pelo VAD, e o início de cada palavra recebe um ajuste de +60 ms (`--ajuste-ms`), porque o Whisper adianta as palavras uns 70 ms (medido).
6. A montagem das legendas usa programação dinâmica dentro de cada frase. Ela penaliza terminar em "de/a/até/que…", premia vírgula e pausa e evita separar "grão | de areia". Depois vem a quebra de linha equilibrada.
7. Cache JSON em `<out>/.cache_legenda/`. A chave é sha256 do áudio + parâmetros do ASR (o alinhamento tem cache próprio por hash do roteiro). Ao refazer estilo, modo ou tradução, o modelo nem é carregado (0,1 s, 24 MB).
8. O modelo é carregado uma vez e liberado (`del` + `gc`) antes de queimar. O pico de RAM vai pro log (Windows: `PeakWorkingSetSize` via ctypes; Linux: `ru_maxrss`).

## ⚠️ compute_type: o padrão é `int16`, não `int8`
No box, o `int8` do CTranslate2 (4.8.2 e também 4.7.1, testado) deu **saída aleatória**: a mesma chamada, repetida, devolve texto diferente ou **vazio**. Isso aconteceu até com 1 thread e com `CT2_PACKED_GEMM=0` ou `CT2_FORCE_CPU_ISA=AVX2`. Há um relato público igual (dev.to, out/2026: "faster-whisper int8 dropped up to 60 s of speech"). O `int16` foi estável (3 de 3 repetições idênticas, e o pipeline inteiro rodado 2x deu saída igual) e usa **~1,3 GB de pico**. O `float32` também é estável, mas pede ~2,2 GB.
**No Junon, rode primeiro:**
```
python junon_legenda.py qualquer_audio.mp3 --autoteste --compute-type int8
python junon_legenda.py qualquer_audio.mp3 --autoteste --compute-type int16
```
Se o `int8` passar ali (outra CPU pode não ter o bug), dá pra usar `--compute-type int8` e economizar ~300-400 MB. Na dúvida, fique com `int16`. **Não use medium** (int16 = 3,6 GB de pico, medido).

## Instalação no Windows (Junon)
1. Python 3.10+ (64 bits). Numa pasta, por exemplo `C:\Junon\legenda\`, copie:
   - `junon_legenda.py`
   - `fontes\InterJunon-Bold.ttf` e `fontes\OFL.txt` (Inter peso 800, OFL 1.1; o libass usa essa pasta automaticamente)
   - opcional: `avaliar.py`, `tests\`, `README.md`
2. Dependências (de preferência num venv):
   ```
   python -m venv C:\Junon\legenda\venv
   C:\Junon\legenda\venv\Scripts\pip install faster-whisper==1.2.1 numpy
   ```
   (no pip, cerca de 150-250 MB: ctranslate2, onnxruntime, tokenizers, av etc.)
3. **ffmpeg + ffprobe** no PATH, com `libass` e `libx264`. A build "essentials" do gyan.dev tem os dois. Confira com `ffmpeg -hide_banner -filters | findstr " ass "`. Também dá pra apontar as variáveis `JUNON_FFMPEG` e `JUNON_FFPROBE` para os .exe.
4. Modelo (cerca de 464 MB). Ou ele baixa sozinho na 1ª execução (Hugging Face `Systran/faster-whisper-small`), ou você copia a pasta pronta (`config.json`, `model.bin`, `tokenizer.json`, `vocabulary.txt`) para, por exemplo, `C:\Junon\modelos\faster-whisper-small` e usa `--modelo C:\Junon\modelos\faster-whisper-small --offline`.
5. Teste: `python -m unittest discover -s tests -v` (12 testes, sem modelo, menos de 1 s) e depois o `--autoteste` acima.

## Uso
```
# SRT do canal, texto = roteiro (bloco ElevenLabs do .md é achado sozinho)
python junon_legenda.py narracao.mp3 --roteiro roteiro.md
# Shorts: palavra a palavra (1-4 palavras)
python junon_legenda.py narracao.mp3 --roteiro roteiro.md --modo palavras
# ASS karaokê (dourado #F2C14E acumulando) / só a palavra atual / sem destaque
python junon_legenda.py video.mp4 --roteiro roteiro.md --modo ass --estilo karaoke
python junon_legenda.py video.mp4 --roteiro roteiro.md --modo ass --estilo palavra
# Queimar no vídeo (2 threads, veryfast, crf 20, prioridade baixa); teste rápido só de 8 s a partir de 20 s:
python junon_legenda.py video.mp4 --roteiro roteiro.md --modo queimar --threads 2 --trecho 20,8
# Só áudio? Queima sobre uma imagem (ou fundo escuro):
python junon_legenda.py narracao.mp3 --modo queimar --fundo capa.jpg
# Sem roteiro (texto do Whisper)
python junon_legenda.py video.mp4
# Tradução (mesmos tempos): exporta as linhas, traduz fora (ou com plugin) e volta
python junon_legenda.py video.mp4 --roteiro r.md --exportar-linhas          # -> video.linhas.txt
python junon_legenda.py video.mp4 --roteiro r.md --traduzir en --tradutor arquivo:video.en.txt
python junon_legenda.py video.mp4 --traduzir en --tradutor py:meu_tradutor:traduzir
```
Saídas (na pasta `--out` ou ao lado da entrada): `nome.srt`, `nome.palavras.srt`, `nome.<estilo>.ass`, `nome.legendado.mp4`, `nome.<lang>.srt`, `nome.palavras.json` (com `--json`: palavra, início e fim, origem `exato/fuzzy/interp(+forcado)`).

Opções úteis: `--threads N` (padrão 4; no Junon, 2-4), `--estilo`, `--fonte "Arial"`, `--tamanho 0.045` (fração da altura; 86 px em 1920), `--cor`, `--destaque "#F2C14E"`, `--contorno-cor`, `--contorno 6`, `--pos-y 0.646` (centro do texto em ≈1240 de 1920, fora da UI do Shorts), `--max-chars 42`, `--max-palavras 4`, `--beam 5`, `--com-contexto`, `--forcado auto|sim|nao`, `--ajuste-ms 60`, `--prompt-roteiro`, `--sem-cache`, `--cache DIR`, `--crf`, `--preset`, `--resolucao 1920x1080` (ASS sem vídeo), `--bloco "título da seção"`.

### Tradução: interface
`traduzir_linhas(linhas, destino, origem="pt", backend)` recebe 1 texto por legenda e devolve a lista traduzida do mesmo tamanho. Os tempos ficam os da legenda original, e o texto é requebrado em 42x2. Backends:
- `arquivo:CAMINHO`: um .txt com uma linha por legenda (`\n` literal = quebra). Serve pra traduzir fora (LLM, DeepL, humano) a partir do `--exportar-linhas`.
- `py:modulo:funcao`: plugin seu, `funcao(linhas, destino, origem) -> list[str]`.
- `argos`/`auto`: usa o **argostranslate** (MIT) **se estiver instalado**. **Não está instalado e não recomendo no Junon**: ele depende do `stanza`, que puxa o **PyTorch** (centenas de MB a GB de disco e RAM). Os modelos pt→en dele têm cerca de 100 MB, mas cada pacote tem a sua licença (confira antes). Sem tradutor, o programa para com uma mensagem clara.

## Números medidos (box Linux, 8 núcleos **compartilhados**, load average 10-20; os tempos variam muito)
Short "lua_buraco_negro" (171 palavras, narração ElevenLabs de 64,9 s; voz editada de 58,7 s).

| Teste | Resultado |
|---|---|
| RAM pico (small int16, 4 threads, transcrição + alinhamento) | **1,27-1,36 GB** (só o modelo carregado: ~1,07 GB) |
| RAM pico, re-execução com cache | 24 MB (0,1 s) |
| RAM pico do ffmpeg queimando 1080x1920 (2 threads) | 343-515 MB (o modelo já foi liberado) |
| Tempo de 64,9 s de áudio (4 threads) | 15,8 s com a máquina menos carregada; 25,7 s com 2 threads; até 72 s com o box muito carregado |
| Alinhamento forçado | +4 a 16 s (só os blocos necessários) |
| Queimar 58,7 s 1080x1920 (veryfast, crf 20, 2 threads) | 40,7 s |
| Texto com roteiro (narração, voz editada, vídeo com música) | **171/171 palavras idênticas ao roteiro, SRT = roteiro caractere a caractere**, sem espaço duplo nem espaço antes de pontuação |
| Sem roteiro | WER 2,9% (voz), 4,1% (voz + música); erros como "espreimida", "seguiam" (por "se guiam"), "para" (por "pra") |
| Tempo de palavra vs SRT do canal (voz_edit.wav, 1ª palavra de cada uma das 60 legendas) | **com roteiro: média 48 ms, mediana 43 ms, p90 104 ms, máx 156 ms; 90% ≤100 ms, 100% ≤200 ms** |
| idem, vídeo final (voz + música + SFX) | média 49 ms, p90 112 ms, máx 142 ms, 100% ≤200 ms |
| idem, sem roteiro | média 73 ms, p90 142 ms, máx 542 ms, 93% ≤200 ms |
| Blocos do modo palavras iguais aos do SRT do canal (feito à mão) | 45 de 63 |
| Determinismo int16 | 2 execuções completas sem cache: saída idêntica |

Obs.: o SRT do canal (`render/lua_buraco_negro.srt`) foi feito sobre a **voz editada** (`voz_edit.wav`, com as pausas encurtadas), não sobre `narracao.mp3`. Por isso a comparação de tempo é feita com o `voz_edit.wav` e com o vídeo final. Para a `narracao.mp3`, a comparação foi com o `medium` (que também é Whisper, então é uma referência fraca): diferença média de 125 ms. O `medium` fica ~100 ms mais tarde que a referência por energia.

## Limites conhecidos
- O `int8` é instável no box (ver acima). No Junon, o `--autoteste` decide.
- Sem roteiro, o texto e a pontuação vêm do Whisper small: erros de grafia, "para" no lugar de "pra" e minúsculas depois de vírgula.
- O alinhamento supõe que o roteiro é o que foi falado e na mesma ordem. Se o locutor pular ou trocar uma frase, as palavras que sobram ficam interpoladas ou espremidas no bloco (a legenda continua mostrando o roteiro).
- Números e siglas lidos de outro jeito ("1,7 K" falado "um vírgula sete kelvin") não casam exato. O alinhamento forçado resolve o tempo, mas a legenda mostra o texto do roteiro.
- A tradução depende de um backend externo (nenhum offline leve disponível).
- Os estilos ASS são simples (sem animação de escala/pop). O tamanho por caractere é estimado (0,56 em) para o limite de largura: fontes muito largas podem precisar de `--tamanho` menor.
- Os tempos não foram medidos no Windows do Junon. A RAM deve ser parecida (o modelo é o mesmo). O tempo depende da CPU dele.

## Licenças
| Componente | Licença |
|---|---|
| faster-whisper 1.2.1 | MIT |
| CTranslate2 | MIT |
| Modelo Whisper small (OpenAI) / conversão Systran | MIT |
| Silero VAD (vem dentro do faster-whisper) | MIT |
| onnxruntime | MIT |
| tokenizers, huggingface_hub | Apache-2.0 |
| PyAV (dependência do faster-whisper; não usamos pra decodificar) | BSD-3 |
| numpy | BSD-3 |
| ffmpeg (programa externo) / libass / libx264 | LGPL-2.1+ / ISC / GPL-2 (build com x264 = GPL; só executamos o binário) |
| Fonte Inter (fontes/InterJunon-Bold.ttf, instância estática 800) | SIL OFL 1.1 |
| argostranslate (opcional, NÃO instalado) | MIT (+ stanza Apache-2.0 + PyTorch BSD; modelos com licenças próprias) |

## Arquivos
- `junon_legenda.py`: o programa
- `avaliar.py`: métricas (texto vs roteiro, tempo vs SRT/JSON de referência)
- `tests/test_legenda.py`: testes unitários (sem modelo); `tests/teste_real.sh`: o teste com o Short real
- `fontes/`: Inter 800 + licença
- `saida/`: saídas dos testes descritos acima (SRT/ASS/JSON e 3 vídeos curtos), 2 MB, pode apagar
- `PROGRESS.md`
