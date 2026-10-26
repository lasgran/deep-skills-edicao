#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""junon_legenda.py - gerador de legendas (pt-BR) para os canais e para o Junon.

Fluxo: áudio/vídeo -> ffmpeg (16 kHz mono) -> faster-whisper small int8 (tempos por palavra)
-> [opcional] alinha o ROTEIRO às palavras reconhecidas (texto = roteiro, tempo = Whisper)
-> SRT (estilo canal ou palavra-a-palavra) / ASS (karaokê) / vídeo com legenda queimada.

Dependências: faster-whisper (MIT), numpy (BSD), ffmpeg no PATH (LGPL/GPL, chamado como programa).
Só stdlib no resto. Ver README.md.
"""
from __future__ import annotations

import argparse
import difflib
import gc
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from dataclasses import dataclass, asdict, field
from pathlib import Path

VERSAO = "1.0"
CACHE_VERSAO = 1  # muda se o formato do cache mudar


def log(msg: str):
    print(f"[legenda {time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ----------------------------------------------------------------------------- RAM
def pico_ram_mb() -> float:
    """Pico de memória (RSS / working set) do próprio processo, em MB. Sem dependências."""
    try:
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes

            class PMC(ctypes.Structure):
                _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                            ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                            ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
            pmc = PMC(); pmc.cb = ctypes.sizeof(PMC)
            k32 = ctypes.windll.kernel32
            k32.GetCurrentProcess.restype = wintypes.HANDLE
            ctypes.windll.psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb)
            return pmc.PeakWorkingSetSize / 2**20
        import resource
        r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return r / 2**20 if sys.platform == "darwin" else r / 1024
    except Exception:
        return -1.0


# ----------------------------------------------------------------------------- ffmpeg
def _flags_baixa_prioridade():
    if os.name == "nt":
        return {"creationflags": 0x00004000}  # BELOW_NORMAL_PRIORITY_CLASS
    return {"preexec_fn": lambda: os.nice(10)}


def ffmpeg_bin() -> str:
    return os.environ.get("JUNON_FFMPEG", "ffmpeg")


def carregar_audio(caminho: str, sr: int = 16000):
    """Decodifica com o ffmpeg direto para PCM 16 kHz mono e devolve float32 numpy.
    Contorno do bug do faster-whisper.decode_audio (metadata_errors) com PyAV 19."""
    import numpy as np
    cmd = [ffmpeg_bin(), "-nostdin", "-v", "error", "-i", caminho, "-vn", "-ac", "1", "-ar", str(sr),
           "-f", "s16le", "-acodec", "pcm_s16le", "-"]
    p = subprocess.run(cmd, capture_output=True)
    if p.returncode != 0 or not p.stdout:
        raise RuntimeError("ffmpeg falhou ao ler o áudio: " + p.stderr.decode("utf-8", "replace")[-500:])
    return np.frombuffer(p.stdout, np.int16).astype(np.float32) / 32768.0


def sonda_video(caminho: str):
    """(largura, altura, duração) via ffprobe; None se não tiver vídeo."""
    ffprobe = os.environ.get("JUNON_FFPROBE", "ffprobe")
    try:
        out = subprocess.run([ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries",
                              "stream=width,height:format=duration", "-of", "json", caminho],
                             capture_output=True, text=True, check=True).stdout
        j = json.loads(out)
        st = j.get("streams") or []
        if not st:
            return None
        return int(st[0]["width"]), int(st[0]["height"]), float(j.get("format", {}).get("duration", 0) or 0)
    except Exception:
        return None


def hash_arquivo(caminho: str) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


# ----------------------------------------------------------------------------- transcrição
@dataclass
class ParamsASR:
    modelo: str = "small"
    compute_type: str = "int16"         # int8 deu saída aleatória/vazia no box (CT2 4.7.1 e 4.8.2), ver README
    language: str = "pt"
    beam_size: int = 5
    vad_filter: bool = True              # usa o Silero VAD para achar as pausas e cortar o áudio em blocos
    bloco_max_s: float = 24.0            # blocos curtos: o small "pula" trechos em janelas de 30 s
    bloco_min_s: float = 6.0
    condition_on_previous_text: bool = False
    initial_prompt: str | None = None

    def chave(self) -> dict:
        return asdict(self)


SR = 16000


def _fala_vad(audio) -> list[tuple[float, float]]:
    from faster_whisper.vad import VadOptions, get_speech_timestamps
    ts = get_speech_timestamps(audio, VadOptions(min_silence_duration_ms=150, speech_pad_ms=30))
    return [(t["start"] / SR, t["end"] / SR) for t in ts]


def planejar_blocos(fala: list[tuple[float, float]], total: float, max_s=24.0, min_s=6.0) -> list[tuple[float, float]]:
    """Corta a linha do tempo nas pausas (as maiores possíveis) em blocos de min_s..max_s."""
    if not fala:
        return [(0.0, min(total, max_s))] if total > 0 else []
    gaps = [(fala[i][1], fala[i + 1][0]) for i in range(len(fala) - 1)]
    blocos = []
    cur = max(0.0, fala[0][0] - 0.3)
    fim = min(total, fala[-1][1] + 0.3)
    while fim - cur > max_s:
        cand = [g for g in gaps if cur + min_s <= (g[0] + g[1]) / 2 <= cur + max_s]
        if cand:
            g = max(cand, key=lambda g: (round(g[1] - g[0], 2), g[0]))
            corte = (g[0] + g[1]) / 2
        else:
            corte = cur + max_s
        blocos.append((cur, corte)); cur = corte
    blocos.append((cur, fim))
    return [(round(a, 3), round(b, 3)) for a, b in blocos if b - a > 0.2]


def _tira_repeticoes(ws: list[dict]) -> list[dict]:
    """Remove n-gramas repetidos em sequência (alucinação típica: 'a massa é a mesma, a massa é a mesma')."""
    mudou = True
    while mudou:
        mudou = False
        N = [normalizar(w["w"]) for w in ws]
        for n in range(8, 1, -1):
            for i in range(0, len(ws) - 2 * n + 1):
                if N[i:i + n] == N[i + n:i + 2 * n]:
                    del ws[i + n:i + 2 * n]; mudou = True
                    break
            if mudou:
                break
    return ws


def _encaixar_na_fala(words: list[dict], fala: list[tuple[float, float]]):
    """Puxa começo/fim de palavra que caiu em silêncio para a borda da fala (VAD)."""
    if not fala:
        return words
    import bisect
    ini = [a for a, _ in fala]
    for w in words:
        i = bisect.bisect_right(ini, w["s"]) - 1
        if i < 0 or w["s"] > fala[i][1]:          # começa num silêncio -> próximo início de fala
            j = i + 1
            if j < len(fala) and fala[j][0] < w["e"]:
                w["s"] = round(fala[j][0], 3)
        k = bisect.bisect_right(ini, w["e"]) - 1
        if k >= 0 and w["e"] > fala[k][1] + 0.05 and fala[k][1] > w["s"]:  # termina num silêncio
            w["e"] = round(fala[k][1] + 0.05, 3)
        if w["e"] <= w["s"]:
            w["e"] = round(w["s"] + 0.05, 3)
    return words


class Motor:
    """Carrega o modelo uma vez (só se precisar: cache cheio não carrega nada) e libera no fim."""

    def __init__(self, p: ParamsASR, threads=4, download_root=None, offline=False):
        self.p, self.threads, self.download_root, self.offline = p, threads, download_root, offline
        self.model = None
        self._audio = {}
        self.t_carregar = 0.0

    def modelo(self):
        if self.model is None:
            t = time.time()
            from faster_whisper import WhisperModel
            self.model = WhisperModel(self.p.modelo, device="cpu", compute_type=self.p.compute_type,
                                      cpu_threads=self.threads, num_workers=1,
                                      download_root=self.download_root, local_files_only=self.offline)
            self.t_carregar = time.time() - t
            log(f"modelo {self.p.modelo}/{self.p.compute_type} carregado em {self.t_carregar:.1f}s "
                f"(RAM pico {pico_ram_mb():.0f} MB)")
        return self.model

    def audio(self, caminho):
        if caminho not in self._audio:
            self._audio = {caminho: carregar_audio(caminho)}
        return self._audio[caminho]

    def liberar(self):
        self.model = None
        self._audio = {}
        gc.collect()

    # --- reconhecimento por blocos
    def _asr_bloco(self, audio, a: float, b: float, fala, prof=0) -> list[dict]:
        m = self.modelo()
        c = audio[int(a * SR):int(b * SR)]
        segs, _ = m.transcribe(c, language=self.p.language, beam_size=self.p.beam_size, vad_filter=False,
                               word_timestamps=True, condition_on_previous_text=self.p.condition_on_previous_text,
                               initial_prompt=self.p.initial_prompt)
        ws = []
        for s in segs:
            ruim = s.temperature > 0.5 or s.avg_logprob < -1.0 or s.compression_ratio > 2.4
            if ruim:
                continue
            for w in (s.words or []):
                t = w.word.strip()
                if t:
                    ws.append({"w": t, "s": round(a + w.start, 3), "e": round(a + w.end, 3), "p": round(w.probability, 3)})
        ws = _tira_repeticoes(ws)
        fala_s = sum(max(0.0, min(b, y) - max(a, x)) for x, y in fala)
        taxa = len(ws) / fala_s if fala_s > 0 else 9
        if taxa < 1.3 and (b - a) > 5 and prof < 2:   # o small pulou um pedaço: divide e tenta de novo
            sub = planejar_blocos([(max(a, x), min(b, y)) for x, y in fala if y > a and x < b], b,
                                  max_s=(b - a) / 2 + 1.5, min_s=min(3.0, (b - a) / 4))
            sub = [(max(a, x), min(b, y)) for x, y in sub]
            if len(sub) > 1:
                log(f"  bloco {a:.1f}-{b:.1f}s: só {len(ws)} palavras ({taxa:.1f}/s de fala), refazendo em {len(sub)} partes")
                novo = []
                for x, y in sub:
                    novo += self._asr_bloco(audio, x, y, fala, prof + 1)
                if len(novo) > len(ws):
                    ws = novo
        return ws

    def transcrever(self, caminho: str, cache_dir: str | None) -> dict:
        chave = {"v": CACHE_VERSAO, "audio_sha256": hash_arquivo(caminho), **self.p.chave()}
        self.audio_hash = chave["audio_sha256"]
        hk = hashlib.sha256(json.dumps(chave, sort_keys=True).encode()).hexdigest()[:20]
        cpath = None
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)
            cpath = os.path.join(cache_dir, f"{Path(caminho).stem}.asr.{hk}.json")
            if os.path.exists(cpath):
                with open(cpath, encoding="utf-8") as f:
                    d = json.load(f)
                log(f"cache ASR: {os.path.basename(cpath)} ({len(d['words'])} palavras) - pulando transcrição")
                d["info"]["do_cache"] = True
                return d
        t0 = time.time()
        audio = self.audio(caminho)
        total = len(audio) / SR
        fala = _fala_vad(audio) if self.p.vad_filter else [(0.0, total)]
        blocos = planejar_blocos(fala, total, self.p.bloco_max_s, self.p.bloco_min_s) if self.p.vad_filter \
            else [(x, min(total, x + 30.0)) for x in [i * 30.0 for i in range(int(total // 30) + 1)] if x < total]
        t1 = time.time()
        words = []
        for a, b in blocos:
            words += self._asr_bloco(audio, a, b, fala)
        words.sort(key=lambda w: w["s"])
        _encaixar_na_fala(words, fala)
        t2 = time.time()
        d = {"words": words, "blocos": blocos, "fala": [(round(a, 3), round(b, 3)) for a, b in fala],
             "duracao": round(total, 3),
             "info": {"tempo_audio_vad_s": round(t1 - t0, 2), "tempo_carregar_s": round(self.t_carregar, 2),
                      "tempo_transcrever_s": round(t2 - t1 - self.t_carregar, 2), "ram_pico_mb": round(pico_ram_mb()),
                      "threads": self.threads, "blocos": len(blocos), "do_cache": False}}
        log(f"transcrito {total:.1f}s de áudio em {t2 - t1:.1f}s ({len(blocos)} blocos): {len(words)} palavras; "
            f"RAM pico {pico_ram_mb():.0f} MB")
        if cpath:
            with open(cpath, "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False, indent=0)
        return d

    # --- alinhamento forçado do roteiro (texto conhecido -> tempos), bloco a bloco
    def alinhar_forcado(self, caminho: str, asr: dict, rough: list[dict], cache_dir: str | None,
                        modo: str = "auto") -> list[dict]:
        """modo 'sim': todos os blocos; 'auto': só blocos com palavra não-exata (fuzzy/interpolada)."""
        toks = [w["w"] for w in rough]
        chave = {"v": CACHE_VERSAO, "audio_sha256": getattr(self, "audio_hash", None) or hash_arquivo(caminho),
                 "modelo": self.p.modelo, "ct": self.p.compute_type, "blocos": asr["blocos"],
                 "roteiro": hashlib.sha256("\n".join(toks).encode()).hexdigest(), "modo": modo}
        hk = hashlib.sha256(json.dumps(chave, sort_keys=True).encode()).hexdigest()[:20]
        cpath = os.path.join(cache_dir, f"{Path(caminho).stem}.alin.{hk}.json") if cache_dir else None
        if cpath and os.path.exists(cpath):
            log(f"cache alinhamento: {os.path.basename(cpath)}")
            with open(cpath, encoding="utf-8") as f:
                return json.load(f)
        t0 = time.time()
        from faster_whisper.audio import pad_or_trim
        from faster_whisper.tokenizer import Tokenizer
        m = self.modelo()
        tk = Tokenizer(m.hf_tokenizer, m.model.is_multilingual, task="transcribe", language=self.p.language)
        audio = self.audio(caminho)
        total = len(audio) / SR
        blocos = asr["blocos"]
        # cada palavra do roteiro vai pro bloco onde caiu o meio do tempo aproximado
        grupo = [[] for _ in blocos]
        for k, w in enumerate(rough):
            mid = (w["s"] + w["e"]) / 2
            bi = next((i for i, (a, b) in enumerate(blocos) if mid < b), len(blocos) - 1)
            grupo[bi].append(k)
        out = [dict(w) for w in rough]
        feitos = 0
        for (a, b), ks in zip(blocos, grupo):
            if not ks:
                continue
            if modo == "auto" and all(rough[k].get("fonte") == "exato" for k in ks):
                continue
            feitos += 1
            a2, b2 = max(0.0, a - 0.15), min(total, b + 0.15)
            c = audio[int(a2 * SR):int(b2 * SR)]
            try:
                feats = m.feature_extractor(c)
                nf = min(int(round(len(c) / m.feature_extractor.hop_length)), 3000)
                enc = m.encode(pad_or_trim(feats))
                texto = " " + " ".join(toks[k] for k in ks)
                ids = tk.encode(texto)
                res = m.find_alignment(tk, [ids], enc, nf)[0]
            except Exception as ex:  # mantém o aproximado
                log(f"  alinhamento forçado falhou no bloco {a:.1f}-{b:.1f}: {ex}")
                continue
            # mapeia as "palavras" do tokenizer de volta pras palavras do roteiro (por posição de caractere)
            spans, pos = [], 1
            for k in ks:
                spans.append((pos, pos + len(toks[k]))); pos += len(toks[k]) + 1
            acc = 0
            tempos = {}
            for r in res:
                wtxt = r["word"]
                p0 = acc + (len(wtxt) - len(wtxt.lstrip()))
                acc += len(wtxt)
                if not wtxt.strip():
                    continue
                j = next((jj for jj, (x, y) in enumerate(spans) if x <= p0 < y), None)
                if j is None:
                    continue
                st, en = a2 + float(r["start"]), a2 + float(r["end"])
                if j in tempos:
                    s0, e0, pr = tempos[j]
                    if normalizar(wtxt):  # pontuação solta não estica o fim
                        e0 = max(e0, en)
                    tempos[j] = (min(s0, st), e0, pr)
                else:
                    tempos[j] = (st, en, float(r["probability"]))
            for j, k in enumerate(ks):
                if j in tempos:
                    s, e, pr = tempos[j]
                    out[k].update(s=round(s, 3), e=round(max(e, s + 0.04), 3), p=round(pr, 3),
                                  fonte=out[k].get("fonte", "") + "+forcado")
        _encaixar_na_fala(out, [tuple(x) for x in asr.get("fala", [])])
        ult = 0.0
        for w in out:  # monotônico
            if w["s"] < ult:
                w["s"] = ult
            w["e"] = max(w["e"], w["s"] + 0.04)
            ult = w["s"]
        log(f"alinhamento forçado ({feitos}/{len(blocos)} blocos, modo {modo}) em {time.time() - t0:.1f}s; RAM pico {pico_ram_mb():.0f} MB")
        if cpath:
            with open(cpath, "w", encoding="utf-8") as f:
                json.dump(out, f, ensure_ascii=False, indent=0)
        return out


# ----------------------------------------------------------------------------- texto / roteiro
TAG_RE = re.compile(r"\[[^\]\n]{1,40}\]|<[^>\n]{1,80}/?>")  # [curious], [whispers], <break time="1s"/>
FECHA = ",.;:!?…)]}»”"
ABRE = "([{«“"
DASH = "—–-"
FUNCIONAIS = set("""a o as os um uma uns umas e ou de do da dos das no na nos nas em ao aos à às
pra pro pras pros por pelo pela pelos pelas com sem que se sobre até para mas lhe me te
the of to and in""".split())


def _base(t: str) -> str:
    """minúsculas sem pontuação, MANTENDO acentos (pra distinguir 'é' de 'e', 'à' de 'a')."""
    return re.sub(r"[^\w]", "", t.lower())


def normalizar(t: str) -> str:
    t = unicodedata.normalize("NFKD", t.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^0-9a-z]+", "", t)


def arrumar_espacos(t: str) -> str:
    t = t.replace("\u00a0", " ")
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"\s+([,.;:!?…)\]}»”])", r"\1", t)          # sem espaço antes de fecha/pontuação
    t = re.sub(r"([(\[{«“])\s+", r"\1", t)                  # sem espaço depois de abre
    t = re.sub(r"([,;:!?…])(?=[^\s\d,.;:!?…)\]}»”\"'])", r"\1 ", t)  # espaço depois (não em 1,7)
    t = re.sub(r"(?<=[a-zà-ú])\.(?=[A-ZÀ-Ú])", ". ", t)     # "fim.Começo" -> "fim. Começo"
    t = re.sub(r"\.\.\.(?=[A-Za-zÀ-ú])", "... ", t)          # "mar...nem" -> "mar... nem"
    return re.sub(r" {2,}", " ", t)


def extrair_roteiro(texto: str, bloco: str | None = None) -> str:
    """De um .md/.txt, devolve só o texto falado. Em .md tenta achar a seção ElevenLabs
    (ou a seção cujo título contém `bloco`); senão usa o arquivo todo sem markdown."""
    linhas = texto.splitlines()
    alvo = (bloco or "elevenlabs").lower()
    ini = None
    nivel = 0
    for i, l in enumerate(linhas):
        m = re.match(r"^(#{1,6})\s+(.*)", l)
        if m and alvo in m.group(2).lower():
            ini, nivel = i + 1, len(m.group(1))
            break
    if ini is not None:
        fim = len(linhas)
        for j in range(ini, len(linhas)):
            m = re.match(r"^(#{1,6})\s+", linhas[j])
            if m and len(m.group(1)) <= nivel:
                fim = j
                break
        linhas = linhas[ini:fim]
    elif bloco:
        raise ValueError(f"seção '{bloco}' não encontrada no roteiro")
    out = []
    for l in linhas:
        s = l.strip()
        if not s or s.startswith(("#", "|", ">", "```", "---")):
            continue
        s = re.sub(r"^[-*+]\s+|^\d+[.)]\s+", "", s)
        s = re.sub(r"[*_`]{1,3}", "", s)
        out.append(s)
    t = TAG_RE.sub(" ", " ".join(out))
    return arrumar_espacos(t)


def tokenizar(texto: str) -> list[str]:
    """Separa em palavras mantendo a pontuação grudada. Pontuação solta vai pra palavra vizinha."""
    toks: list[str] = []
    pend = ""
    for t in texto.split():
        if normalizar(t):
            if pend:
                t = pend + t; pend = ""
            toks.append(t)
        elif toks and t[0] not in ABRE:
            toks[-1] += (" " + t) if t[0] in DASH else t
        else:
            pend += t if t[0] in ABRE else t + " "
    if pend and toks:
        toks[-1] += " " + pend.strip()
    return toks


# ----------------------------------------------------------------------------- alinhamento
def _sim(a: str, b: str) -> float:
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def _alinhar_trecho(S: list[str], A: list[str]) -> list[tuple]:
    """Needleman-Wunsch num trecho: devolve [(i_script, j0_asr, j1_asr)] dos casados (1:1, 1:2, 2:1)."""
    n, m = len(S), len(A)
    if n == 0 or m == 0:
        return []
    GAP = -0.4
    NEG = -1e9
    sc = [[NEG] * (m + 1) for _ in range(n + 1)]
    bk = [[None] * (m + 1) for _ in range(n + 1)]
    sc[0][0] = 0.0
    for i in range(n + 1):
        for j in range(m + 1):
            if i == 0 and j == 0:
                continue
            best, arg = NEG, None
            if i and sc[i - 1][j] > NEG and sc[i - 1][j] + GAP > best:
                best, arg = sc[i - 1][j] + GAP, ("s",)
            if j and sc[i][j - 1] > NEG and sc[i][j - 1] + GAP > best:
                best, arg = sc[i][j - 1] + GAP, ("a",)
            if i and j:
                v = sc[i - 1][j - 1] + (_sim(S[i - 1], A[j - 1]) * 2 - 0.8)
                if v > best:
                    best, arg = v, ("m",)
            if i and j >= 2:  # uma palavra do roteiro = duas do ASR ("guiam" ~ "gui am")
                v = sc[i - 1][j - 2] + (_sim(S[i - 1], A[j - 2] + A[j - 1]) * 2 - 1.0)
                if v > best:
                    best, arg = v, ("m12",)
            if i >= 2 and j:  # duas do roteiro = uma do ASR
                v = sc[i - 2][j - 1] + (_sim(S[i - 2] + S[i - 1], A[j - 1]) * 2 - 1.0)
                if v > best:
                    best, arg = v, ("m21",)
            sc[i][j], bk[i][j] = best, arg
    res = []
    i, j = n, m
    while i or j:
        op = bk[i][j][0]
        if op == "s":
            i -= 1
        elif op == "a":
            j -= 1
        elif op == "m":
            if _sim(S[i - 1], A[j - 1]) >= 0.5:
                res.append((i - 1, j - 1, j - 1))
            i -= 1; j -= 1
        elif op == "m12":
            if _sim(S[i - 1], A[j - 2] + A[j - 1]) >= 0.6:
                res.append((i - 1, j - 2, j - 1))
            i -= 1; j -= 2
        else:  # m21: divide o tempo da palavra do ASR entre as duas
            if _sim(S[i - 2] + S[i - 1], A[j - 1]) >= 0.6:
                res.append((i - 2, j - 1, j - 1, "a"))
                res.append((i - 1, j - 1, j - 1, "b"))
            i -= 2; j -= 1
    return res[::-1]


def alinhar_roteiro(script_tokens: list[str], asr: list[dict]) -> tuple[list[dict], dict]:
    """Casa as palavras do roteiro com as do Whisper. Texto = roteiro; tempo = Whisper.
    Âncoras exatas via difflib; trechos divergentes via NW fuzzy; o resto é interpolado."""
    S = [normalizar(t) for t in script_tokens]
    A = [normalizar(w["w"]) for w in asr]
    n = len(S)
    tempos: list[tuple | None] = [None] * n
    tipo = ["interp"] * n
    sm = difflib.SequenceMatcher(None, S, A, autojunk=False)
    for tag, i0, i1, j0, j1 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i1 - i0):
                w = asr[j0 + k]
                tempos[i0 + k] = (w["s"], w["e"]); tipo[i0 + k] = "exato"
        elif tag == "replace" and (i1 - i0) * (j1 - j0) <= 400 * 400:
            for r in _alinhar_trecho(S[i0:i1], A[j0:j1]):
                i, a0, a1 = r[0] + i0, r[1] + j0, r[2] + j0
                s, e = asr[a0]["s"], asr[a1]["e"]
                if len(r) == 4:  # m21
                    mid = (s + e) / 2
                    s, e = (s, mid) if r[3] == "a" else (mid, e)
                tempos[i] = (s, e); tipo[i] = "fuzzy"
    # interpola os que sobraram, proporcional ao nº de letras
    fim_audio = asr[-1]["e"] if asr else 0.0
    i = 0
    while i < n:
        if tempos[i] is not None:
            i += 1; continue
        j = i
        while j < n and tempos[j] is None:
            j += 1
        t0 = tempos[i - 1][1] if i > 0 else max(0.0, (tempos[j][0] if j < n else 0.0) - 0.35 * (j - i))
        t1 = tempos[j][0] if j < n else max(t0 + 0.35 * (j - i), fim_audio)
        if t1 <= t0:
            t1 = t0 + 0.05 * (j - i)
        pesos = [max(1, len(S[k])) + 1 for k in range(i, j)]
        tot = sum(pesos); acc = t0
        for k, pw in zip(range(i, j), pesos):
            d = (t1 - t0) * pw / tot
            tempos[k] = (acc, acc + d); acc += d
        i = j
    out = []
    ult = 0.0
    for k, tok in enumerate(script_tokens):
        s, e = tempos[k]
        s = max(s, ult)                    # monotônico
        e = max(e, s + 0.04)
        out.append({"w": tok, "s": round(s, 3), "e": round(e, 3), "fonte": tipo[k]})
        ult = s
    est = {"palavras_roteiro": n, "palavras_asr": len(asr), "exatas": tipo.count("exato"),
           "fuzzy": tipo.count("fuzzy"), "interpoladas": tipo.count("interp")}
    return out, est


# ----------------------------------------------------------------------------- montagem das legendas
@dataclass
class Cue:
    ini: float
    fim: float
    words: list = field(default_factory=list)   # dicts {'w','s','e'}
    linhas: list = field(default_factory=list)  # listas de índices em words por linha

    def texto(self, sep="\n") -> str:
        return sep.join(arrumar_espacos(" ".join(self.words[k]["w"] for k in ln)) for ln in self.linhas)


def _fim_frase(w: str) -> bool:
    return w.rstrip("”\"')»").endswith((".", "?", "!", "…"))


def _pont(w: str) -> bool:
    return w.rstrip("”\"')»").endswith((",", ";", ":", "—", "–")) or _fim_frase(w)


def _comp(ws: list[dict]) -> int:
    return len(arrumar_espacos(" ".join(w["w"] for w in ws)))


def quebrar_linhas(ws: list[dict], max_chars: int, max_linhas: int = 2) -> list[list[int]]:
    if _comp(ws) <= max_chars or len(ws) == 1 or max_linhas == 1:
        return [list(range(len(ws)))]
    best, arg = None, None
    for k in range(1, len(ws)):
        a, b = _comp(ws[:k]), _comp(ws[k:])
        custo = abs(a - b) + (1000 if max(a, b) > max_chars else 0)
        if _pont(ws[k - 1]["w"]):
            custo -= 12
        if _base(ws[k - 1]["w"]) in FUNCIONAIS:
            custo += 10
        if best is None or custo < best:
            best, arg = custo, k
    return [list(range(arg)), list(range(arg, len(ws)))]


PREP_LIGA = {"de", "do", "da", "dos", "das"}
CONJ = {"e", "que", "mas", "ou", "porque", "quando", "se", "com", "sem", "pra", "para", "como", "onde"}


def _custo_bloco(ws, i, j, palav, max_chars, max_linhas, min_dur, fim_frase):
    """Custo de um bloco ws[i:j] (j = índice exclusivo) dentro de uma frase."""
    seg = ws[i:j]
    c = 3.0 if not palav else 1.0
    n = _comp(seg)
    ult = seg[-1]["w"]
    if not fim_frase:
        if _base(ult) in FUNCIONAIS and not _pont(ult):
            c += 6
        if _pont(ult):
            c -= 2
        gap = ws[j]["s"] - seg[-1]["e"]
        c -= min(max(gap, 0.0), 0.5) * 6
        if _base(ws[j]["w"]) in CONJ:
            c -= 1
        if _base(ws[j]["w"]) in PREP_LIGA:  # "grão | de areia" separa o que anda junto
            c += 1.5
    if palav:
        if len(seg) == 1 and not (i == 0 and fim_frase):
            c += 2
        c += abs(n - 12) * 0.15
    else:
        if seg[-1]["e"] - seg[0]["s"] < min_dur:
            c += 4
        if n < 15 and not (i == 0 and fim_frase):
            c += 3
        if n > max_chars:
            lin = quebrar_linhas(seg, max_chars, max_linhas)
            u = seg[lin[0][-1]]["w"]
            if _base(u) in FUNCIONAIS and not _pont(u):
                c += 4
            c += abs(_comp([seg[k] for k in lin[0]]) - _comp([seg[k] for k in lin[-1]])) * 0.05
    return c


def _dividir_frase(ws, palav, cap, max_chars, max_linhas, min_dur, max_dur, max_palavras):
    """Programação dinâmica: melhor jeito de cortar uma frase em blocos que respeitam os limites."""
    n = len(ws)
    INF = float("inf")
    best = [0.0] + [INF] * n
    arg = [0] * (n + 1)
    for j in range(1, n + 1):
        for i in range(j - 1, -1, -1):
            k = j - i
            if palav and k > max_palavras:
                break
            chars = _comp(ws[i:j])
            dur = ws[j - 1]["e"] - ws[i]["s"]
            if k > 1 and (chars > cap or dur > max_dur):
                break
            v = best[i] + _custo_bloco(ws, i, j, palav, max_chars, max_linhas, min_dur, j == n)
            if v < best[j]:
                best[j], arg[j] = v, i
    cortes, j = [], n
    while j > 0:
        cortes.append((arg[j], j)); j = arg[j]
    return [ws[i:j] for i, j in reversed(cortes)]


def agrupar(words: list[dict], modo: str = "canal", max_chars: int = 42, max_linhas: int = 2,
            min_dur: float = 1.0, max_dur: float = 6.0, max_palavras: int = 4, pausa: float | None = None,
            cauda: float = 0.45, lead: float = 0.04) -> list[Cue]:
    """modo 'canal': até max_chars x max_linhas, 1-6 s, quebra na pontuação.
    modo 'palavras': 1-4 palavras (Shorts), quebra em qualquer pontuação e pausa."""
    palav = modo == "palavras"
    if palav:
        cap = max_chars if max_chars < 42 else 20
        pausa = 0.30 if pausa is None else pausa
    else:
        cap = max_chars * max_linhas
        pausa = 0.60 if pausa is None else pausa
    # 1) frases: cortes obrigatórios (fim de frase / qualquer pontuação nos Shorts / pausa longa)
    frases: list[list[dict]] = []
    cur: list[dict] = []
    for w in words:
        if cur:
            prev = cur[-1]
            duro = (w["s"] - prev["e"] >= pausa) or (_pont(prev["w"]) if palav else _fim_frase(prev["w"]))
            if duro:
                frases.append(cur); cur = []
        cur.append(w)
    if cur:
        frases.append(cur)
    # 2) canal: junta frases curtas vizinhas ("As marés? Iguais.") se couberem numa linha
    if not palav:
        jun: list[list[dict]] = []
        for f in frases:
            if jun:
                p = jun[-1]
                curta = p[-1]["e"] - p[0]["s"] < 1.2 and _comp(p) <= max_chars // 2
                cabe = _comp(p + f) <= max_chars or (p[-1]["e"] - p[0]["s"] < min_dur and _comp(p + f) <= cap)
                if curta and cabe and f[-1]["e"] - p[0]["s"] <= max_dur and f[0]["s"] - p[-1]["e"] < pausa:
                    jun[-1] = p + f
                    continue
            jun.append(f)
        frases = jun
    # 3) cada frase vira 1+ blocos (programação dinâmica)
    grupos: list[list[dict]] = []
    for f in frases:
        grupos += _dividir_frase(f, palav, cap, max_chars, max_linhas, min_dur, max_dur, max_palavras)
    cues: list[Cue] = []
    for g, ws in enumerate(grupos):
        ini = max(0.0, ws[0]["s"] - lead)
        prox = grupos[g + 1][0]["s"] - lead if g + 1 < len(grupos) else ws[-1]["e"] + cauda
        fim = min(ws[-1]["e"] + cauda, prox)
        if not palav and fim - ini < min_dur:
            fim = min(ini + min_dur, max(prox, fim))
        if not palav:
            fim = min(fim, ini + max_dur)
        if cues and ini < cues[-1].fim:
            ini = cues[-1].fim
        fim = max(fim, ini + 0.1)
        lin = quebrar_linhas(ws, max_chars if not palav else cap, 1 if palav else max_linhas)
        cues.append(Cue(round(ini, 3), round(fim, 3), ws, lin))
    return cues


# ----------------------------------------------------------------------------- SRT
def ts_srt(x: float) -> str:
    ms = int(round(max(0.0, x) * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def escrever_srt(cues: list[Cue], caminho: str, textos: list[str] | None = None):
    blocos = []
    for n, c in enumerate(cues, 1):
        txt = textos[n - 1] if textos else c.texto()
        blocos.append(f"{n}\n{ts_srt(c.ini)} --> {ts_srt(c.fim)}\n{txt}\n")
    with open(caminho, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(blocos))


def ler_srt(caminho: str) -> list[tuple[float, float, str]]:
    def p(t):
        h, m, r = t.strip().split(":"); s, ms = r.split(",")
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
    out = []
    with open(caminho, encoding="utf-8-sig") as fh:
        conteudo = fh.read().strip()
    for bl in re.split(r"\n\s*\n", conteudo):
        ls = bl.strip().splitlines()
        if len(ls) >= 3 and "-->" in ls[1]:
            a, b = ls[1].split("-->")
            out.append((p(a), p(b), " ".join(ls[2:])))
    return out


# ----------------------------------------------------------------------------- ASS
@dataclass
class EstiloASS:
    fonte: str = "Inter Junon"      # fontes/InterJunon-Bold.ttf (Inter 800, OFL) vai junto
    tamanho: float = 0.045          # fração da altura do vídeo (86 px em 1920) ; >1 = pixels
    cor: str = "#FFFFFF"
    destaque: str = "#F2C14E"
    contorno_cor: str = "#000000"
    contorno: float = 6.0           # px em 1080 de largura (escala com o vídeo)
    sombra: float = 2.0
    negrito: bool = True
    pos_y: float = 0.646            # centro do bloco: 0.646*1920 ≈ 1240 (zona segura dos Shorts)
    margem_x: float = 0.08          # fração da largura de cada lado
    largura_char: float = 0.56      # largura média de um caractere em em (sans bold)


def cor_ass(hexcor: str, alpha: int = 0) -> str:
    h = hexcor.lstrip("#")
    if len(h) != 6:
        raise ValueError(f"cor inválida: {hexcor}")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H{alpha:02X}{b}{g}{r}".upper()


def esc_ass(t: str) -> str:
    return t.replace("\\", "\\\\").replace("{", "(").replace("}", ")")


def ts_ass(x: float) -> str:
    cs = int(round(max(0.0, x) * 100)); h, cs = divmod(cs, 360000); m, cs = divmod(cs, 6000); s, cs = divmod(cs, 100)
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def escrever_ass(cues: list[Cue], caminho: str, estilo: str = "karaoke", W: int = 1080, H: int = 1920,
                 e: EstiloASS | None = None):
    """estilo 'canal' (texto branco, sem destaque), 'karaoke' (\\k: palavras ficam douradas quando
    são faladas) ou 'palavra' (só a palavra atual dourada)."""
    e = e or EstiloASS()
    fs = e.tamanho * H if e.tamanho <= 1 else e.tamanho
    esc = W / 1080.0
    ml = int(W * e.margem_x)
    branco, ouro = cor_ass(e.cor), cor_ass(e.destaque)
    # karaokê: Primary = depois de falado (ouro), Secondary = antes (branco)
    prim, sec = (ouro, branco) if estilo == "karaoke" else (branco, ouro)
    cab = f"""[Script Info]
; gerado por junon_legenda.py {VERSAO}
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Junon,{e.fonte},{fs:.0f},{prim},{sec},{cor_ass(e.contorno_cor)},{cor_ass('#000000', 0x80)},{-1 if e.negrito else 0},0,0,0,100,100,0,0,1,{e.contorno * esc:.1f},{e.sombra * esc:.1f},5,{ml},{ml},0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    x, y = W // 2, int(e.pos_y * H)
    pos = f"{{\\an5\\pos({x},{y})}}"
    ev = []
    for c in cues:
        def linha_txt(fmt_word):
            partes = []
            for ln in c.linhas:
                ws = [fmt_word(k) for k in ln]
                partes.append(" ".join(ws))
            return "\\N".join(partes)
        if estilo == "canal":
            txt = "\\N".join(esc_ass(t) for t in c.texto().split("\n"))
            ev.append(f"Dialogue: 0,{ts_ass(c.ini)},{ts_ass(c.fim)},Junon,,0,0,0,,{pos}{txt}")
        elif estilo == "karaoke":
            t = c.ini
            partes_lin = []
            for ln in c.linhas:
                pw = []
                for k in ln:
                    w = c.words[k]
                    gap = max(0, int(round((w["s"] - t) * 100)))
                    pre = f"{{\\k{gap}}}" if gap else ""
                    nxt = c.words[k + 1]["s"] if k + 1 < len(c.words) else c.fim
                    d = max(1, int(round((max(w["e"], min(nxt, c.fim)) - max(w["s"], t)) * 100)))
                    t = max(w["s"], t) + d / 100
                    pw.append(f"{pre}{{\\k{d}}}{esc_ass(arrumar_espacos(w['w']))}")
                partes_lin.append(" ".join(pw))
            ev.append(f"Dialogue: 0,{ts_ass(c.ini)},{ts_ass(c.fim)},Junon,,0,0,0,,{pos}" + "\\N".join(partes_lin))
        else:  # palavra: um evento por palavra, a ativa em ouro
            for k, w in enumerate(c.words):
                a = c.ini if k == 0 else max(c.ini, w["s"] - 0.02)
                b = c.fim if k + 1 == len(c.words) else max(a + 0.04, c.words[k + 1]["s"] - 0.02)
                def fw(j, k=k):
                    t_ = esc_ass(arrumar_espacos(c.words[j]["w"]))
                    return f"{{\\c{sec}}}{t_}{{\\c{prim}}}" if j == k else t_
                ev.append(f"Dialogue: 0,{ts_ass(a)},{ts_ass(b)},Junon,,0,0,0,,{pos}{linha_txt(fw)}")
    with open(caminho, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write(cab + "\n".join(ev) + "\n")


def max_chars_para(W: int, H: int, e: EstiloASS) -> int:
    fs = e.tamanho * H if e.tamanho <= 1 else e.tamanho
    return max(8, int(W * (1 - 2 * e.margem_x) / (fs * e.largura_char)))


# ----------------------------------------------------------------------------- queimar
def _esc_filtro(p: str) -> str:
    return p.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def queimar(video: str | None, ass: str, saida: str, threads: int = 2, crf: int = 20, preset: str = "veryfast",
            fundo: str | None = None, audio: str | None = None, W: int = 1080, H: int = 1920,
            fontsdir: str | None = None, trecho: tuple[float, float] | None = None, baixa_prioridade=True):
    """Queima o .ass com libass. Se não houver vídeo, usa `fundo` (imagem) ou cor escura + o áudio."""
    ass_dir, ass_nome = os.path.dirname(os.path.abspath(ass)), os.path.basename(ass)
    filtro = f"ass={_esc_filtro(ass_nome)}"
    if fontsdir and os.path.isdir(fontsdir):
        filtro += f":fontsdir={_esc_filtro(os.path.abspath(fontsdir))}"
    cmd = [ffmpeg_bin(), "-nostdin", "-y", "-hide_banner", "-loglevel", "error", "-stats"]
    ss = []
    if trecho:
        ss = ["-ss", f"{trecho[0]:.3f}", "-t", f"{trecho[1]:.3f}"]
        filtro = f"setpts=PTS+{trecho[0]:.3f}/TB,{filtro},setpts=PTS-STARTPTS"
    if video:
        cmd += ss + ["-i", os.path.abspath(video)]
        mapa = ["-map", "0:v:0", "-map", "0:a?"]
    else:
        if fundo:
            cmd += ["-loop", "1", "-framerate", "30", "-i", os.path.abspath(fundo)]
            filtro = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},format=yuv420p," + filtro
        else:
            cmd += ["-f", "lavfi", "-i", f"color=c=0x101018:s={W}x{H}:r=30"]
        cmd += ss + ["-i", os.path.abspath(audio)]
        mapa = ["-map", "0:v:0", "-map", "1:a:0", "-shortest"]
        if trecho:
            filtro = filtro.replace(f"setpts=PTS+{trecho[0]:.3f}/TB,", f"setpts=PTS-STARTPTS+{trecho[0]:.3f}/TB,")
    cmd += mapa + ["-vf", filtro, "-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-pix_fmt", "yuv420p",
                   "-threads", str(threads), "-filter_threads", "1", "-c:a", "aac", "-b:a", "160k",
                   "-movflags", "+faststart", os.path.abspath(saida)]
    log("ffmpeg: " + " ".join(cmd))
    kw = _flags_baixa_prioridade() if baixa_prioridade else {}
    t0 = time.time()
    subprocess.run(cmd, cwd=ass_dir, check=True, **kw)
    extra = ""
    if os.name != "nt":
        import resource
        extra = f"; RAM pico do ffmpeg {resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024:.0f} MB"
    log(f"queimado em {time.time() - t0:.1f}s -> {saida}{extra}")


# ----------------------------------------------------------------------------- tradução (plugável)
def traduzir_linhas(linhas: list[str], destino: str, origem: str = "pt", backend: str = "auto") -> list[str]:
    """Interface: recebe uma lista de textos (uma legenda cada) e devolve a lista traduzida,
    MESMO tamanho e mesma ordem (os tempos ficam os da legenda original).

    backends:
      'arquivo:CAMINHO'   - arquivo .txt já traduzido, uma legenda por linha (use '\\n' p/ quebra)
      'py:modulo:funcao'  - função sua: funcao(linhas, destino, origem) -> list[str]
      'argos'             - argostranslate, se estiver instalado (NÃO vem instalado: puxa torch via stanza)
      'auto'              - argos se existir; senão erro explicativo
    """
    if backend.startswith("arquivo:"):
        with open(backend[8:], encoding="utf-8") as fh:
            tr = fh.read().splitlines()
        tr = [t.replace("\\n", "\n") for t in tr if t.strip()]
        if len(tr) != len(linhas):
            raise ValueError(f"arquivo de tradução tem {len(tr)} linhas, esperado {len(linhas)}")
        return tr
    if backend.startswith("py:"):
        import importlib
        _, mod, fn = backend.split(":", 2)
        res = getattr(importlib.import_module(mod), fn)(linhas, destino, origem)
        if len(res) != len(linhas):
            raise ValueError("tradutor devolveu número diferente de linhas")
        return list(res)
    if backend in ("auto", "argos"):
        try:
            import argostranslate.translate as at  # type: ignore
        except ImportError:
            raise SystemExit(
                "Tradução: nenhum tradutor offline instalado. Opções: --tradutor arquivo:traducao.txt "
                "(uma linha por legenda; gere a lista com --exportar-linhas), --tradutor py:modulo:funcao, "
                "ou instale argostranslate (pesado, ver README).")
        return [at.translate(l.replace("\n", " "), origem, destino) for l in linhas]
    raise ValueError(f"backend de tradução desconhecido: {backend}")


def rewrap(txt: str, max_chars: int, max_linhas: int = 2) -> str:
    ws = [{"w": t} for t in arrumar_espacos(txt.replace("\n", " ")).split(" ") if t]
    if not ws:
        return ""
    return "\n".join(arrumar_espacos(" ".join(ws[k]["w"] for k in ln)) for ln in quebrar_linhas(ws, max_chars, max_linhas))


def autoteste(caminho, modelo="small", compute_type="int16", threads=4, download_root=None, offline=False):
    """Roda o mesmo trecho 2x: se o texto mudar ou vier vazio, esse compute_type não é confiável nesta CPU."""
    from faster_whisper import WhisperModel
    audio = carregar_audio(caminho)[:30 * SR]
    m = WhisperModel(modelo, device="cpu", compute_type=compute_type, cpu_threads=threads, num_workers=1,
                     download_root=download_root, local_files_only=offline)
    txts = []
    for i in range(2):
        t = time.time()
        segs, _ = m.transcribe(audio, language="pt", beam_size=5, vad_filter=False, condition_on_previous_text=False)
        txt = " ".join(s.text.strip() for s in segs)
        txts.append(txt)
        log(f"rodada {i + 1}: {len(txt.split())} palavras em {time.time() - t:.1f}s: {txt[:120]}")
    ok = txts[0] == txts[1] and len(txts[0].split()) >= 0.8 * (len(audio) / SR)
    log(f"AUTOTESTE {compute_type} x{threads} threads: {'OK (estável)' if ok else 'FALHOU (instável/vazio): use int16 ou float32'}"
        f"; RAM pico {pico_ram_mb():.0f} MB")
    return ok


# ----------------------------------------------------------------------------- CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description="Gerador de legendas do Junon (faster-whisper small int8, pt-BR).")
    ap.add_argument("entrada", help="arquivo de áudio ou vídeo")
    ap.add_argument("--roteiro", help="roteiro .txt/.md: o texto da legenda vira o roteiro; o Whisper só dá os tempos")
    ap.add_argument("--bloco", help="título (trecho) da seção do .md com o texto falado (padrão: ElevenLabs)")
    ap.add_argument("--modo", choices=["srt", "ass", "queimar", "palavras"], default="srt")
    ap.add_argument("--estilo", choices=["canal", "karaoke", "palavra"], default=None,
                    help="estilo do ASS (padrão: karaoke em ass/queimar)")
    ap.add_argument("--traduzir", metavar="IDIOMA", help="gera também <nome>.<IDIOMA>.srt com os mesmos tempos")
    ap.add_argument("--tradutor", default="auto", help="backend de tradução (ver README)")
    ap.add_argument("--exportar-linhas", action="store_true", help="salva <nome>.linhas.txt (texto das legendas, uma por linha)")
    ap.add_argument("--out", default=None, help="pasta de saída (padrão: ao lado da entrada)")
    ap.add_argument("--threads", type=int, default=4, help="threads da CPU (whisper e ffmpeg)")
    ap.add_argument("--modelo", default="small", help="small (padrão), base, tiny, ou pasta local do modelo")
    ap.add_argument("--compute-type", default="int16", help="int16 (padrão, estável), int8 (menos RAM; instável no box), float32")
    ap.add_argument("--beam", type=int, default=5)
    ap.add_argument("--com-contexto", action="store_true", help="condition_on_previous_text=True (padrão False: evita loops)")
    ap.add_argument("--forcado", choices=["auto", "sim", "nao"], default="auto",
                    help="com roteiro: alinhamento forçado do texto (auto = só blocos onde o ASR não bateu)")
    ap.add_argument("--prompt-roteiro", action="store_true", help="passa o começo do roteiro como initial_prompt")
    ap.add_argument("--sem-vad", action="store_true")
    ap.add_argument("--cache", default=None, help="pasta do cache JSON (padrão: <out>/.cache_legenda)")
    ap.add_argument("--sem-cache", action="store_true")
    ap.add_argument("--modelos-dir", default=None, help="download_root do faster-whisper")
    ap.add_argument("--offline", action="store_true", help="não baixa nada (local_files_only)")
    ap.add_argument("--max-chars", type=int, default=42)
    ap.add_argument("--ajuste-ms", type=float, default=60, help="soma ao início de cada palavra (Whisper adianta ~70 ms)")
    ap.add_argument("--max-palavras", type=int, default=4)
    # ASS
    ap.add_argument("--fonte", default="Inter Junon", help="nome da família (padrão: a Inter 800 de fontes/)")
    ap.add_argument("--fontes-dir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "fontes"),
                    help="pasta com .ttf para o libass (padrão: fontes/ ao lado do script)")
    ap.add_argument("--tamanho", type=float, default=0.045, help="fração da altura (0.045=86px em 1920) ou px se >1")
    ap.add_argument("--cor", default="#FFFFFF")
    ap.add_argument("--destaque", default="#F2C14E")
    ap.add_argument("--contorno-cor", default="#000000")
    ap.add_argument("--contorno", type=float, default=6.0)
    ap.add_argument("--pos-y", type=float, default=0.646, help="centro vertical da legenda (fração da altura)")
    ap.add_argument("--resolucao", default=None, help="LxA do ASS quando não há vídeo (padrão 1080x1920)")
    # queimar
    ap.add_argument("--video", default=None, help="vídeo onde queimar (se a entrada for só áudio)")
    ap.add_argument("--fundo", default=None, help="imagem de fundo se não houver vídeo")
    ap.add_argument("--crf", type=int, default=20)
    ap.add_argument("--preset", default="veryfast")
    ap.add_argument("--trecho", default=None, help="INI,DUR em segundos: queima só um pedaço (teste)")
    ap.add_argument("--json", action="store_true", help="salva também <nome>.palavras.json (texto+tempos finais)")
    ap.add_argument("--autoteste", action="store_true",
                    help="transcreve os primeiros 30 s duas vezes e diz se o compute_type está estável nesta CPU")
    a = ap.parse_args(argv)
    for s in (sys.stdout, sys.stderr):  # console/pipe do Windows (cp1252) não quebra com "…"
        try:
            s.reconfigure(errors="replace")
        except Exception:
            pass

    t_ini = time.time()
    ent = os.path.abspath(a.entrada)
    if not os.path.exists(ent):
        ap.error(f"não achei {ent}")
    out = os.path.abspath(a.out or os.path.dirname(ent))
    os.makedirs(out, exist_ok=True)
    nome = Path(ent).stem
    info_v = sonda_video(ent)
    video = ent if info_v else (os.path.abspath(a.video) if a.video else None)
    if video and not info_v:
        info_v = sonda_video(video)
    if a.resolucao:
        W, H = (int(v) for v in a.resolucao.lower().split("x"))
    elif info_v:
        W, H = info_v[0], info_v[1]
    else:
        W, H = 1080, 1920

    if a.autoteste:
        return autoteste(ent, a.modelo, a.compute_type, a.threads, a.modelos_dir, a.offline)
    roteiro_txt = None
    if a.roteiro:
        with open(a.roteiro, encoding="utf-8-sig") as fh:
            roteiro_txt = extrair_roteiro(fh.read(), a.bloco)
        log(f"roteiro: {len(roteiro_txt.split())} palavras (tags de emoção removidas)")
    p = ParamsASR(modelo=a.modelo, compute_type=a.compute_type, beam_size=a.beam, vad_filter=not a.sem_vad,
                  condition_on_previous_text=a.com_contexto,
                  initial_prompt=(roteiro_txt[:400] if (a.prompt_roteiro and roteiro_txt) else None))
    cache = None if a.sem_cache else (a.cache or os.path.join(out, ".cache_legenda"))
    motor = Motor(p, threads=a.threads, download_root=a.modelos_dir, offline=a.offline)
    tr = motor.transcrever(ent, cache)
    asr = tr["words"]
    if not asr:
        raise SystemExit("nenhuma fala reconhecida")
    est = None
    if roteiro_txt:
        words, est = alinhar_roteiro(tokenizar(roteiro_txt), asr)
        log(f"alinhamento com o roteiro: {est}")
        if a.forcado != "nao":
            words = motor.alinhar_forcado(ent, tr, words, cache, a.forcado)
    else:
        words = [{"w": w["w"], "s": w["s"], "e": w["e"], "fonte": "asr"} for w in asr]
    motor.liberar()
    del motor
    if a.ajuste_ms:  # o alinhamento do Whisper adianta o início das palavras (~60-80 ms medidos)
        aj = a.ajuste_ms / 1000.0
        for w in words:
            w["s"] = round(max(0.0, min(w["s"] + aj, w["e"] - 0.04)), 3)

    e = EstiloASS(fonte=a.fonte, tamanho=a.tamanho, cor=a.cor, destaque=a.destaque, contorno_cor=a.contorno_cor,
                  contorno=a.contorno, pos_y=a.pos_y)
    saidas = []
    if a.modo == "srt":
        cues = agrupar(words, "canal", max_chars=a.max_chars)
        f = os.path.join(out, f"{nome}.srt"); escrever_srt(cues, f); saidas.append(f)
    elif a.modo == "palavras":
        cues = agrupar(words, "palavras", max_palavras=a.max_palavras, max_chars=min(a.max_chars, 20))
        f = os.path.join(out, f"{nome}.palavras.srt"); escrever_srt(cues, f); saidas.append(f)
    else:
        estilo = a.estilo or "karaoke"
        mc = max_chars_para(W, H, e)
        if estilo == "canal":
            cues = agrupar(words, "canal", max_chars=min(a.max_chars, mc))
        else:
            cues = agrupar(words, "palavras", max_palavras=a.max_palavras, max_chars=min(20, mc))
        f = os.path.join(out, f"{nome}.{estilo}.ass"); escrever_ass(cues, f, estilo, W, H, e); saidas.append(f)
        if a.modo == "queimar":
            trecho = tuple(float(x) for x in a.trecho.split(",")) if a.trecho else None
            if not video and not a.fundo:
                log("sem vídeo: queimando sobre fundo escuro (use --video ou --fundo)")
            v_out = os.path.join(out, f"{nome}.legendado.mp4")
            queimar(video, f, v_out, threads=a.threads, crf=a.crf, preset=a.preset, fundo=a.fundo,
                    audio=ent, W=W, H=H, fontsdir=a.fontes_dir, trecho=trecho)
            saidas.append(v_out)
    if a.json:
        f = os.path.join(out, f"{nome}.palavras.json")
        with open(f, "w", encoding="utf-8") as fh:
            json.dump({"words": words, "alinhamento": est, "asr_info": tr["info"]}, fh, ensure_ascii=False, indent=0)
        saidas.append(f)
    if a.traduzir or a.exportar_linhas:
        base = cues if a.modo in ("srt",) else agrupar(words, "canal", max_chars=a.max_chars)
        linhas = [c.texto() for c in base]
        if a.exportar_linhas:
            f = os.path.join(out, f"{nome}.linhas.txt")
            with open(f, "w", encoding="utf-8") as fh:
                fh.write("\n".join(l.replace("\n", "\\n") for l in linhas) + "\n")
            saidas.append(f)
        if a.traduzir:
            trd = traduzir_linhas(linhas, a.traduzir, "pt", a.tradutor)
            f = os.path.join(out, f"{nome}.{a.traduzir}.srt")
            escrever_srt(base, f, [rewrap(t, a.max_chars) for t in trd]); saidas.append(f)
    log(f"pronto em {time.time() - t_ini:.1f}s; RAM pico do processo {pico_ram_mb():.0f} MB")
    for s in saidas:
        print(s)
    return saidas


if __name__ == "__main__":
    main()
