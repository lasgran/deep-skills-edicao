---
name: vector-anime-drawing
description: >-
  Use when drawing anime/chibi characters or illustrations, either as
  code-generated SVG imported into a vector editor (VectorCraft etc.), via Krita
  bridge ops, or by mouse in a paint app: construction, anatomy, layer order,
  shading, hair, hands, folds, original characters.
---
# Desenho anime/chibi — método

## Pipeline
1. Gerar geometria por código (Python): funções reutilizáveis, nada à mão.
2. Renderizar local (cairosvg) → OLHAR o PNG → corrigir, parte por parte.
3. VectorCraft: `document.open {path: x.svg}` → `file.saveAs` → `document.export png`.
4. Krita: operações JSON pela ponte (camadas, preenchimentos, traços afinados, presets de pincel, maskBy, soften, export), em estágios, exportando após cada um.

## Ordem e camadas
construção → contornos grandes → detalhes → line-art → cores chapadas → cel 2–3 tons → pintura suave → highlights → efeitos.
Camadas: fundo, cabelo-trás, corpo, rosto, olhos, cabelo-frente, acessórios, efeitos. Cada forma com o próprio contorno (oclusão correta).
Chibi: cabeça ≈ 55–60% da altura, olhos grandes na metade inferior.

## Funções úteis
`lock()` mecha afinada; `leaf()` gomo de trança sobreposto (ângulo ±0.5 rad); `eye()` branco → íris gradiente recortada → sombra da pálpebra → pupila → reflexos → pálpebra afinada com cílio; `ell()` com 4 béziers (sem arcos se espelhar).

## Cor e sombra
Paleta limitada; line-art roxo-escuro (#2b2238). Sombras coloridas a 0.4–0.6 recortadas pela forma. Cabelo com gradiente + angel ring. Recriar por níveis de tom dá faixas: suavizar.

## Mouse (Paint etc.)
Grosso→fino; béziers amostrados a 2–5 px num movimento contínuo; afinar pontas trocando tamanho; contornos fechados com sobreposição; conferir ferramenta ativa com traço de teste; screenshot após cada parte. Traçar referência: vtracer/potrace → vpype → movimentos.

## Anatomia e personagem original
1. Adulto anime ≈ 6.5–7.5 cabeças; olhos na linha média; olho ≈ 1/5 da face com um olho de vão; nariz na metade olhos–queixo; boca a 1/3 nariz–queixo; pescoço ≈ metade da mandíbula.
2. Cabeça = bola 3D + mandíbula; traços em coordenadas de superfície projetadas com yaw/pitch/roll; contorno como envoltória.
3. Pose: esqueleto (keypoints estilo OpenPose) → volumes → contornos.
4. Nunca copiar pixels de arte alheia como original; keypoints públicos ok.

## Lições da rodada 2
1. Gesto primeiro: 3–4 miniaturas de composição numa folha, escolher a mais dinâmica que mantém os objetos-chave claros.
2. Ponto de contato é geometria: definir o toque na superfície 3D e construir a mão a partir dele, com pequena sombra.
3. Mãos: dedos como cadeias de cápsulas (falanges ≈ 0.48/0.30/0.24), curvatura crescendo pra ponta, médio mais longo, vincos, unhas, sombra multiply; punho de manga esconde a palma.
4. Cabelo: 3–5 massas → tufos cônicos de tamanhos variados, vãos triangulares diferentes; raiz estreita (sem topo quadrado); linhas internas leves que somem antes da raiz; cunhas de oclusão; brilho em poucos arcos longos quebrados; fios soltos só na silhueta e presos a uma massa.
5. Peso de linha pela luz: lado iluminado fino e interrompido, lado de sombra grosso; linhas como polígonos preenchidos.
6. Dobras com causa: tubo pendendo dos ombros, tensão rumo ao braço erguido, zigue-zague sob punho empurrado, espiral no antebraço, queda em cordões; cunha fina no lado de sombra + suavizar.
7. Pincéis Krita: Airbrush Soft para volume/blush/bokeh, Ink-2 Fineliner para fios, Pencil-4 Soft em hachuras curtas (multiply ~0.45) para textura; Chalk Grainy via paintPath carimba retângulos, evitar; sempre recortar com maskBy.
8. Escuros com contenção: sombra multiply nunca cobre o rosto inteiro; camadas de sombra 0.5–0.6, blocos grandes suavizados (raio 10–14).
9. Pintura por cima: cel → aerógrafo de volume → textura → oclusão → luz de recorte (Screen, cor de destaque) → brilhos especulares → glow ≤ 0.6 → fios soltos.
10. Crítica: vista inteira + zoom em olhos, mão e franja; nomear defeitos concretos, corrigir, re-renderizar; ≥ 3 passes, o último no render real do Krita.

## Nível honesto
Decalque guiado chega perto do original. Do zero por código sai visual vetorial limpo, abaixo de ilustração profissional; gargalos: dedos, brilho de cabelo, renderização pictórica.
