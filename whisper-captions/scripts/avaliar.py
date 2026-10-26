#!/usr/bin/env python3
"""Mede tempo de palavra e exatidão do texto. Uso:
  python avaliar.py saida.palavras.json --roteiro roteiro.md [--ref-srt ref.srt] [--ref-json outro.palavras.json] [--srt gerado.srt]
--ref-srt: SRT de referência cujo início de cada legenda = início da 1ª palavra - 0,04 s (padrão do ui.py do canal).
--ref-json: outro palavras.json (ex.: medium) com as mesmas palavras do roteiro: compara palavra a palavra."""
import argparse, json, statistics as st, difflib, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import junon_legenda as j


def resumo(err):
    a = sorted(abs(x) for x in err)
    if not a:
        return "sem pares"
    p90 = a[min(len(a) - 1, int(0.9 * len(a)))]
    return (f"n={len(a)} média={st.mean(a)*1000:.0f} ms mediana={st.median(a)*1000:.0f} ms p90={p90*1000:.0f} ms "
            f"máx={a[-1]*1000:.0f} ms  ≤100ms={sum(x<=0.1 for x in a)/len(a):.0%} ≤200ms={sum(x<=0.2 for x in a)/len(a):.0%} "
            f"viés={st.mean(err)*1000:+.0f} ms")


def wer(ref, hyp):
    R = [j.normalizar(t) for t in ref]; H = [j.normalizar(t) for t in hyp]
    d = list(range(len(H) + 1))
    for i in range(1, len(R) + 1):
        p, d[0] = d[0], i
        for k in range(1, len(H) + 1):
            p, d[k] = d[k], min(d[k] + 1, d[k - 1] + 1, p + (R[i - 1] != H[k - 1]))
    return d[len(H)] / max(1, len(R))


ap = argparse.ArgumentParser()
ap.add_argument("palavras"); ap.add_argument("--roteiro"); ap.add_argument("--ref-srt"); ap.add_argument("--ref-json")
ap.add_argument("--srt")
a = ap.parse_args()
W = json.load(open(a.palavras, encoding="utf-8"))["words"]
script = j.tokenizar(j.extrair_roteiro(open(a.roteiro, encoding="utf-8").read())) if a.roteiro else None
if script:
    hyp = [w["w"] for w in W]
    print(f"texto: {len(hyp)} palavras; idênticas ao roteiro (com pontuação): "
          f"{sum(x == y for x, y in zip(hyp, script))}/{len(script)}; WER (sem pontuação) = {wer(script, hyp):.1%}")
if a.srt and script:
    txt = j.arrumar_espacos(" ".join(c[2] for c in j.ler_srt(a.srt)))
    alvo = j.arrumar_espacos(" ".join(script))
    print(f"SRT == roteiro (texto completo, caractere a caractere): {txt == alvo}")
    if txt != alvo:
        for op in difflib.SequenceMatcher(None, alvo, txt).get_opcodes():
            if op[0] != "equal":
                print("  dif:", op[0], repr(alvo[op[1]:op[2]]), "->", repr(txt[op[3]:op[4]]))
    import re
    print("  espaços duplos:", "  " in txt, "| espaço antes de pontuação:", bool(re.search(r" [,.;:!?…]", txt)),
          "| pontuação colada:", bool(re.search(r"[,;:!?…][A-Za-zÀ-ú]", txt)))
if a.ref_srt:
    cues = j.ler_srt(a.ref_srt)
    ref_toks = [t for c in cues for t in c[2].split()]
    starts, i = [], 0
    for c in cues:
        starts.append((i, c[0] + 0.04 if c[0] > 0 else None)); i += len(c[2].split())
    if [j.normalizar(t) for t in ref_toks] != [j.normalizar(w["w"]) for w in W]:
        sm = difflib.SequenceMatcher(None, [j.normalizar(t) for t in ref_toks], [j.normalizar(w["w"]) for w in W])
        mapa = {}
        for b in sm.get_matching_blocks():
            for k in range(b.size):
                mapa[b.a + k] = b.b + k
    else:
        mapa = {k: k for k in range(len(ref_toks))}
    err = [W[mapa[i]]["s"] - t for i, t in starts if t is not None and i in mapa]
    print("início de palavra vs ref SRT (1ª palavra de cada legenda):", resumo(err))
if a.ref_json:
    R = json.load(open(a.ref_json, encoding="utf-8"))["words"]
    sm = difflib.SequenceMatcher(None, [j.normalizar(w["w"]) for w in R], [j.normalizar(w["w"]) for w in W], autojunk=False)
    es, ee = [], []
    for b in sm.get_matching_blocks():
        for k in range(b.size):
            es.append(W[b.b + k]["s"] - R[b.a + k]["s"]); ee.append(W[b.b + k]["e"] - R[b.a + k]["e"])
    print("início vs ref JSON:", resumo(es)); print("fim    vs ref JSON:", resumo(ee))
