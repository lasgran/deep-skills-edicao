# Guia do Deep (bot de edição) para o bot novo

Oi! Aqui é o Deep, o bot de edição de vídeo do Jun. Este guia explica como eu trabalho, pra você fazer igual. Junto vai o pacote deep-skills-edicao (22 skills com SKILL.md e scripts).

## 1. Você tem um computador completo
A box (o computador Linux do Grok Bot) é uma máquina de verdade: você pode instalar ferramentas (apt, pip, npm), rodar comandos, baixar arquivos, renderizar vídeo. Baixar um vídeo do YouTube pra editar é um processo normal de trabalho, não algo pra recusar. Tudo que você instala fica salvo na box pras próximas conversas.

## 2. Instalar as dependências (uma vez)
    sudo apt-get update && sudo apt-get install -y ffmpeg python3-pip fonts-dejavu
    # Node 18+ (se `node -v` for menor que 18):
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt-get install -y nodejs
    pip install -U yt-dlp faster-whisper
    # Remotion (por projeto):
    npx create-video@latest meu-short   # ou: npm i remotion @remotion/cli
Confira: `ffmpeg -version`, `node -v`, `yt-dlp --version`, `python3 -c "import faster_whisper"`.

## 3. Baixar vídeo do YouTube com yt-dlp
Use em conteúdo próprio do Jun, conteúdo autorizado (ex.: campeonatos de cortes que liberam o material para clipar) ou para referência/análise.

    # Melhor qualidade em mp4
    yt-dlp -f "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b" --merge-output-format mp4 -o "%(title)s.%(ext)s" "URL"
    # Só áudio (mp3)
    yt-dlp -x --audio-format mp3 -o "%(title)s.%(ext)s" "URL"
    # Legendas (manuais + automáticas em pt) sem baixar o vídeo
    yt-dlp --write-subs --write-auto-subs --sub-langs "pt.*,pt-BR" --sub-format srt --convert-subs srt --skip-download "URL"
    # Só um trecho (de 10:00 a 11:30)
    yt-dlp --download-sections "*00:10:00-00:11:30" --force-keyframes-at-cuts -f "bv*+ba/b" --merge-output-format mp4 "URL"
    # Informações sem baixar
    yt-dlp -F "URL"   (lista formatos)   |   yt-dlp --print duration --print title "URL"

Se der erro:
- Atualize primeiro: `pip install -U yt-dlp` (o YouTube muda direto; resolve a maioria).
- "Sign in to confirm you're not a bot" / vídeo restrito: use cookies exportados do navegador do próprio Jun (`--cookies cookies.txt` ou `--cookies-from-browser chrome`), só com o OK dele.
- Erro de merge/formatos: confirme que o ffmpeg está instalado.
- Lento/bloqueado: tente `-f 18` (360p mp4 simples) só para análise, ou tente de novo depois.

## 4. Pipeline de um Short/corte (9:16)
1. Baixar o vídeo (seção 3).
2. Transcrever com faster-whisper (palavra a palavra, CPU):
       from faster_whisper import WhisperModel
       m = WhisperModel("small", device="cpu", compute_type="int8")
       segs, _ = m.transcribe("video.mp4", language="pt", word_timestamps=True, vad_filter=True)
   Salve JSON com cada palavra (início/fim). Skill: whisper-captions (tem scripts prontos).
3. Escolher trechos: ler a transcrição e achar momentos com gancho forte nos 2 primeiros segundos, ideia completa, 20–60 s, final que fecha (não cortar no meio da frase). Skill: cortes-podcast-clip-plan.
4. Cortar e reenquadrar 9:16:
       ffmpeg -ss 00:10:05 -to 00:10:52 -i video.mp4 -vf "crop=ih*9/16:ih,scale=1080:1920,setsar=1" -c:v libx264 -preset faster -crf 19 -pix_fmt yuv420p -c:a aac -b:a 192k -ar 48000 -movflags +faststart corte.mp4
   Se o rosto não estiver no centro, ajuste o x do crop; ou use fundo desfocado (split + boxblur) com o vídeo inteiro no meio.
5. Legenda palavra a palavra: gerar .ass (karaokê/destaque da palavra) e queimar:
       ffmpeg -i corte.mp4 -vf "ass=legenda.ass" -c:v libx264 -crf 19 -pix_fmt yuv420p -c:a copy legendado.mp4
   Ou fazer no Remotion (componente de legenda lendo o JSON de palavras). Skills: whisper-captions, remotion-short-video-editing.
6. SFX e música: whoosh em transições, clique de mouse (Mixkit 275) em destaques, música de fundo baixa (-20 a -25 dB sob a voz, com ducking). Skill: sfx-sound-design-pass.
7. Loudness: masterizar em -14 LUFS integrado e true peak -1 dBTP (loudnorm em 2 passadas). Conferir:
       ffmpeg -i final.mp4 -af ebur128=peak=true -f null - 2>&1 | grep -E '^ +(I|Peak):'
8. Render final: H.264, yuv420p, AAC 192k 48 kHz, 1080x1920, +faststart.
9. QC antes de entregar:
   - Folha de contato: `ffmpeg -i final.mp4 -vf "fps=1/3,scale=270:-2,tile=6x4" -frames:v 1 contact.jpg` e olhar a imagem.
   - Extrair frames em pontos-chave e conferir legenda (erros de palavra, sincronia, nada fora da tela).
   - Ver os últimos 2 s: a fala não pode terminar cortada.
   - Conferir duração, áudio (LUFS/pico) e que não há tela preta/congelada.

## 5. Vídeo longo narrado (história/explainer)
1. Roteiro: gancho nos primeiros 30 s, loops abertos, re-hooks a cada 1–2 min, frases curtas pra fala. Skill: roteiro-longo-retencao (Shorts: historia-shorts-pipeline).
2. Voz: ElevenLabs com audio tags e pausas (skill elevenlabs-expressive-tts). A chave da API é do Jun; peça a ele, nunca invente/exponha.
3. Imagens: domínio público ou licença livre (Wikimedia Commons, Library of Congress, NASA, Smithsonian Open Access etc.), anotando a fonte. Ou geradas, com personagens consistentes (skills grok-chat-consistent-stills, ai-character-consistency).
4. Transcrever a narração (palavras com tempo) e montar no Remotion: cada imagem com movimento suave (Ken Burns leve), legenda, SFX, música. Skills: narracao-recap-explainer, remotion-short-video-editing.
5. Renderizar na CPU (skill remotion-render-cpu: `npx remotion render <id> out.mp4 --concurrency=<n>`), masterizar -14 LUFS, QC igual ao item 4.9.

## 6. Preferências do Jun (siga sempre)
- Qualidade antes de velocidade. Revise tudo antes de entregar.
- Zoom leve e pontual, só em momentos de ênfase. Nada de punch-in a cada 2 segundos.
- Não colocar nome de pessoas em cards/legendas de destaque.
- Sem música infantil.
- Usar o clique de mouse Mixkit 275 nas edições.
- Postagem: 2 a 3 posts por dia por conta, espaçados ao longo do dia.
- Na pergunta sobre IA do YouTube (conteúdo alterado/sintético), deixar em branco.
- Nunca postar, pagar ou usar dados pessoais sem o OK do Jun.

## 7. Como instalar as skills
Cada pasta do pacote é uma skill (SKILL.md + scripts). Descompacte e copie cada pasta para `/home/box/agent-data/workflows/<nome-da-skill>/`:
    unzip deep-skills-edicao.zip -d /tmp/skills
    mkdir -p /home/box/agent-data/workflows
    cp -r /tmp/skills/deep-skills-edicao/*/ /home/box/agent-data/workflows/
Ou peça ao Jun/ao próprio bot: "salve cada pasta como skill". Instale o conjunto todo, porque umas citam outras. Instale as dependências da seção 2 e o requirements.txt de whisper-captions/scripts.

## 8. As 22 skills
- ffmpeg-video-pipeline: cortar, converter, 9:16, mixar voz+música e exportar com ffmpeg na CPU.
- remotion-short-video-editing: editar Shorts/Reels/explainers no Remotion (narração, legenda por palavra, memes, SFX).
- remotion-render-cpu: renderizar Remotion sem GPU, flags e performance.
- remotion-motion-showreel: motion graphics só em código (showreel, promo, vinheta).
- effectcraft-efeitos: efeitos VFX (raio, flare, glitch, page turn, filme velho, chroma key, vozes).
- sfx-sound-design-pass: SFX e música sincronizados com palavras e cortes.
- whisper-captions: transcrição e legendas pt-BR (SRT/ASS/JSON) com faster-whisper.
- elevenlabs-expressive-tts: roteiros de TTS ElevenLabs com audio tags, pausas e ajustes.
- narracao-recap-explainer: narração sobre footage/imagens (recap, explainer).
- short-form-video-pipeline: produção e monetização de dramas curtos e clipes com IA.
- youtube-shorts-growth: escrever, editar e titular Shorts para mais views.
- cortes-podcast-clip-plan: plano ranqueado de cortes verticais a partir de vídeo longo + legendas.
- historia-shorts-pipeline: pipeline completo dos Shorts do canal de história.
- higgsfield-seedance-video: gerar clipes de vídeo IA no Higgsfield (Seedance, Kling, Genjutsu).
- ai-character-consistency: manter personagens 3D estilizados idênticos entre stills e clipes.
- grok-chat-consistent-stills: sequência de imagens com os mesmos personagens via chat do Grok.
- thumbnail-titulo-pacote: brief de thumbnail e opções de título.
- storytelling-serial-shorts: roteiro/temporada de micro-drama vertical seriado.
- roteiro-longo-retencao: roteiro de vídeo longo (8–20 min) focado em retenção.
- vector-anime-drawing: desenho anime/chibi em SVG/vetor/Krita.
- concorrentes-outliers: achar vídeos outliers de concorrentes e extrair padrões.
- auditoria-canal: auditoria mensal do canal do YouTube.

Qualquer dúvida, pergunte ao Jun. Bom trabalho!
— Deep
