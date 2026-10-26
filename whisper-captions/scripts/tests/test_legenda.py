# -*- coding: utf-8 -*-
"""Testes sem modelo (rápidos). Rodar: python -m unittest discover -s tests -v"""
import os, sys, json, tempfile, unittest, wave, shutil
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import junon_legenda as j

ROTEIRO_MD = """# Título
| tabela | x |
## (a) edição
texto que não é falado
## (b) Versão ElevenLabs (texto falado)

[curious] E se a Lua fosse espremida até virar um grão de areia? Um buraco negro. [playful] E o mar… nem ia perceber.
[whispers] As marés? Iguais. E o Sol segue ajudando, com quase metade da força.

## (c) Fontes
nada
"""


def palavras_falsas(tokens, t0=0.0, passo=0.3, pausa_em=()):
    out, t = [], t0
    for i, w in enumerate(tokens):
        out.append({"w": w, "s": round(t, 3), "e": round(t + passo * 0.8, 3)})
        t += passo + (0.7 if i in pausa_em else 0)
    return out


class TestTexto(unittest.TestCase):
    def test_extrair_bloco_elevenlabs_e_tags(self):
        t = j.extrair_roteiro(ROTEIRO_MD)
        self.assertTrue(t.startswith("E se a Lua"))
        self.assertNotIn("[", t); self.assertNotIn("não é falado", t); self.assertNotIn("nada", t)
        self.assertIn("E o mar… nem ia perceber.", t)

    def test_txt_simples(self):
        self.assertEqual(j.extrair_roteiro("Olá , mundo [sighs] !  Tudo bem?"), "Olá, mundo! Tudo bem?")

    def test_espacos(self):
        c = j.arrumar_espacos
        self.assertEqual(c("a ,b  .  c"), "a, b. c")
        self.assertEqual(c("E o mar… nem"), "E o mar… nem")
        self.assertEqual(c("E o mar...nem"), "E o mar... nem")
        self.assertEqual(c("1,7 K"), "1,7 K")
        self.assertEqual(c("( oi )"), "(oi)")
        self.assertEqual(c("fim.Começo"), "fim. Começo")

    def test_tokenizar_pontuacao_solta(self):
        self.assertEqual(j.tokenizar("Olá — tudo bem ? sim"), ["Olá —", "tudo", "bem?", "sim"])
        self.assertEqual(j.tokenizar("« Oi » disse"), ["«Oi»", "disse"])


class TestAlinhamento(unittest.TestCase):
    def test_roteiro_com_erros_do_asr(self):
        script = j.tokenizar(j.extrair_roteiro(ROTEIRO_MD))
        asr = palavras_falsas([j.normalizar(w) for w in script])
        asr[5]["w"] = "espreimida"                      # erro de grafia
        del asr[10:12]                                  # ASR pulou 2 palavras
        asr.insert(3, {"w": "lua", "s": asr[3]["s"], "e": asr[3]["e"]})  # repetição
        words, est = j.alinhar_roteiro(script, asr)
        self.assertEqual([w["w"] for w in words], script)          # texto = roteiro, sempre
        self.assertEqual(est["interpoladas"], 2)
        ss = [w["s"] for w in words]
        self.assertEqual(ss, sorted(ss))                           # monotônico
        self.assertTrue(all(w["e"] > w["s"] for w in words))

    def test_palavra_dividida_no_asr(self):
        script = ["Besouros", "que", "se", "guiam", "pelo", "luar"]
        asr = palavras_falsas(["besouros", "que", "segui", "am", "pelo", "luar"])
        words, est = j.alinhar_roteiro(script, asr)
        self.assertEqual(est["interpoladas"], 0)
        self.assertEqual(words[3]["fonte"], "fuzzy")   # "guiam" casou com "segui"+"am"/fuzzy
        self.assertEqual(len(words), 6)
        self.assertLess(words[2]["s"], words[4]["s"])


class TestBlocos(unittest.TestCase):
    def setUp(self):
        self.script = j.tokenizar(j.extrair_roteiro(ROTEIRO_MD))
        self.w = palavras_falsas(self.script, pausa_em=(11,))

    def test_canal(self):
        cues = j.agrupar(self.w, "canal")
        self.assertEqual(sum(len(c.words) for c in cues), len(self.w))
        for a, b in zip(cues, cues[1:]):
            self.assertLessEqual(a.fim, b.ini + 1e-6)
        for c in cues:
            linhas = c.texto().split("\n")
            self.assertLessEqual(len(linhas), 2)
            self.assertTrue(all(len(l) <= 42 for l in linhas), linhas)
            self.assertLessEqual(c.fim - c.ini, 6.0 + 1e-6)
            self.assertNotIn("  ", c.texto())
        self.assertEqual(j.arrumar_espacos(" ".join(c.texto(" ") for c in cues)), " ".join(self.script))

    def test_palavras(self):
        cues = j.agrupar(self.w, "palavras")
        for c in cues:
            self.assertTrue(1 <= len(c.words) <= 4)
            self.assertLessEqual(len(c.texto()), 20)
        txt = [c.texto() for c in cues]
        self.assertIn("um grão de areia?", txt)
        self.assertFalse(any(t.endswith((" até", " de", " a")) for t in txt), txt)


class TestSaidas(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.w = palavras_falsas(j.tokenizar(j.extrair_roteiro(ROTEIRO_MD)))

    def tearDown(self):
        shutil.rmtree(self.d)

    def test_srt_ida_e_volta(self):
        cues = j.agrupar(self.w, "canal")
        f = os.path.join(self.d, "a.srt"); j.escrever_srt(cues, f)
        lido = j.ler_srt(f)
        self.assertEqual(len(lido), len(cues))
        self.assertAlmostEqual(lido[0][0], cues[0].ini, places=3)
        self.assertEqual(j.ts_srt(3725.5), "01:02:05,500")

    def test_ass(self):
        self.assertEqual(j.cor_ass("#F2C14E"), "&H004EC1F2")
        cues = j.agrupar(self.w, "palavras")
        for est in ("karaoke", "palavra", "canal"):
            f = os.path.join(self.d, f"a.{est}.ass"); j.escrever_ass(cues, f, est)
            with open(f, encoding="utf-8-sig") as fh:
                s = fh.read()
            self.assertIn("PlayResY: 1920", s); self.assertIn("\\pos(540,1240)", s)
            if est == "karaoke":
                self.assertIn("\\k", s); self.assertIn(",&H004EC1F2,&H00FFFFFF,", s)
            if est == "palavra":
                self.assertIn("{\\c&H004EC1F2}", s)

    def test_traducao_arquivo(self):
        f = os.path.join(self.d, "t.txt")
        with open(f, "w", encoding="utf-8") as fh:
            fh.write("one\ntwo\\nlines\n")
        self.assertEqual(j.traduzir_linhas(["um", "dois"], "en", backend="arquivo:" + f), ["one", "two\nlines"])
        with self.assertRaises(ValueError):
            j.traduzir_linhas(["um"], "en", backend="arquivo:" + f)


class TestCache(unittest.TestCase):
    def test_cache_pula_transcricao(self):
        if not shutil.which(j.ffmpeg_bin()):
            self.skipTest("sem ffmpeg")
        d = tempfile.mkdtemp()
        try:
            wav = os.path.join(d, "x.wav")
            with wave.open(wav, "wb") as wf:
                wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(16000); wf.writeframes(b"\x00\x10" * 16000)
            chamadas = []
            orig_vad, orig_asr = j._fala_vad, j.Motor._asr_bloco
            j._fala_vad = lambda a: [(0.1, 0.9)]
            j.Motor._asr_bloco = lambda self, audio, a, b, fala, prof=0: chamadas.append(1) or [{"w": "oi", "s": 0.2, "e": 0.5, "p": 1}]
            try:
                m = j.Motor(j.ParamsASR())
                r1 = m.transcrever(wav, os.path.join(d, "c"))
                r2 = j.Motor(j.ParamsASR()).transcrever(wav, os.path.join(d, "c"))
                r3 = j.Motor(j.ParamsASR(beam_size=1)).transcrever(wav, os.path.join(d, "c"))  # outro parâmetro
            finally:
                j._fala_vad, j.Motor._asr_bloco = orig_vad, orig_asr
            self.assertEqual(len(chamadas), 2)
            self.assertTrue(r2["info"]["do_cache"]); self.assertFalse(r3["info"]["do_cache"])
            self.assertEqual(r1["words"], r2["words"])
        finally:
            shutil.rmtree(d)


if __name__ == "__main__":
    unittest.main()
