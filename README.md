# deep-skills-edicao

Skills de edição de vídeo, áudio, legendas, efeitos e roteiro para Grok Bot. Cada pasta é uma skill independente com um `SKILL.md` (frontmatter `name` + `description`) e, às vezes, scripts auxiliares.

## Skills

| Skill | O que faz |
|---|---|
| ffmpeg-video-pipeline | Editar, cortar, escalar 9:16, mixar e exportar vídeo com ffmpeg na CPU |
| remotion-short-video-editing | Editar Shorts/Reels/explainers no Remotion (narração, legenda por palavra, memes, SFX) |
| remotion-render-cpu | Renderizar Remotion sem GPU, flags e performance |
| remotion-motion-showreel | Motion graphics só em código (showreel, promo, vinheta) |
| effectcraft-efeitos | Efeitos de motion/VFX (raio, flare, glitch, chroma key etc.) |
| sfx-sound-design-pass | Passada de SFX e música sincronizada a palavras/beats |
| whisper-captions | Transcrição e legendas pt-BR (SRT/ASS/JSON) com faster-whisper |
| elevenlabs-expressive-tts | Roteiros para TTS ElevenLabs com audio tags, pausas e ajustes |
| narracao-recap-explainer | Narração sobre footage existente (recap, explainer) |
| short-form-video-pipeline | Produção e monetização de dramas curtos/clipes com IA |
| youtube-shorts-growth | Escrever, editar e titular Shorts para maximizar views |
| cortes-podcast-clip-plan | Plano de cortes verticais a partir de vídeo longo + legendas |
| historia-shorts-pipeline | Pipeline completo de Shorts de história |
| higgsfield-seedance-video | Gerar clipes de vídeo IA no Higgsfield (Seedance, Kling, Genjutsu) |
| ai-character-consistency | Manter personagens 3D estilizados idênticos entre stills e clipes |
| grok-chat-consistent-stills | Sequência de stills consistentes via chat do Grok |
| thumbnail-titulo-pacote | Pacote de thumbnail + título de vídeo |
| storytelling-serial-shorts | Roteiro/temporada de micro-drama vertical seriado |
| roteiro-longo-retencao | Roteiro de vídeo longo (8–20 min) com foco em retenção |
| vector-anime-drawing | Desenho anime/chibi em SVG/vetor/Krita |
| concorrentes-outliers | Pesquisa de vídeos outliers de concorrentes no YouTube/TikTok/Reels |
| auditoria-canal | Auditoria periódica de canal do YouTube |

## Como instalar num Grok Bot novo

Cada pasta é uma skill. Copie a pasta inteira (com `SKILL.md` e arquivos auxiliares) para o diretório de skills do bot (`/home/box/agent-data/workflows/<nome-da-skill>/`) ou peça ao bot: "clone github.com/<usuario>/deep-skills-edicao e instale cada pasta como skill". Algumas skills citam outras pelo nome (ex.: `historia-shorts-pipeline`), então instale o conjunto.

## Dependências

- **ffmpeg / ffprobe** (com libx264, libass)
- **Node.js 18+ e Remotion** (`npx create-video`, `npx remotion render`); Chromium headless do Remotion
- **Python 3.10+** com **faster-whisper** (`whisper-captions/scripts/requirements.txt`), modelo `Systran/faster-whisper-small`
- Opcional: chave **ElevenLabs** (TTS), chave **Higgsfield** (`HF_KEY="id:secret"`, via variável de ambiente — nunca commite), Krita/Inkscape para vetor, Pillow

Nenhuma credencial está incluída neste repositório.
