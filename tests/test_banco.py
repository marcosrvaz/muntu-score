"""Banco curado — bridge de embeddings + retrieval híbrido (mocks, sem rede)."""
import json

from muntu import banco


def test_banco_indisponivel_sem_env(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    assert banco.banco_disponivel() is False
    assert banco.busca_hibrida(texto="x") == []      # best-effort: [] sem crash


def test_embed_texto_via_openrouter(monkeypatch):
    class R:
        def raise_for_status(self):
            pass

        def json(self):
            return {"data": [{"index": 1, "embedding": [0.2] * 1536},
                             {"index": 0, "embedding": [0.1] * 1536}]}

    import httpx
    monkeypatch.setenv("MUNTU_MOOD_API_KEY", "k")
    monkeypatch.setattr(httpx, "post", lambda *a, **kw: R())
    out = banco.embed_texto(["a", "b"])
    assert len(out[0]) == 1536
    assert out[0][0] == 0.1                    # reordenado por index


def test_embed_texto_sem_key_retorna_vazio(monkeypatch):
    monkeypatch.delenv("MUNTU_MOOD_API_KEY", raising=False)
    assert banco.embed_texto(["abc"]) == []


def test_embed_audio_via_subprocess(monkeypatch):
    class R:
        returncode = 0
        stdout = json.dumps({"vetores": [[0.1] * 512]})
        stderr = ""
    monkeypatch.setenv("MUNTU_EMBED_PYTHON", "/fake/python")
    monkeypatch.setattr(banco.subprocess, "run", lambda *a, **kw: R())
    assert len(banco.embed_audio(["a.mp3"])[0]) == 512


def test_embed_audio_sem_venv_retorna_vazio(monkeypatch):
    monkeypatch.delenv("MUNTU_EMBED_PYTHON", raising=False)
    assert banco.embed_audio(["a.mp3"]) == []


def test_busca_hibrida_monta_rpc(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://fake.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "fake-key")
    chamadas = {}

    class FakeClient:
        def rpc(self, nome, params):
            chamadas["nome"], chamadas["params"] = nome, params

            class E:
                def execute(self):
                    class R:
                        data = [{"pointer": "p.mp3", "rrf": 0.03}]
                    return R()
            return E()

    monkeypatch.setattr(banco, "_client", lambda: FakeClient())
    monkeypatch.setattr(banco, "embed_texto", lambda t: [[0.1] * 1536])
    out = banco.busca_hibrida(texto="80s ballad", era="1980s", n=5)
    assert chamadas["nome"] == "busca_hibrida"
    assert chamadas["params"]["filtro_era"] == "1980s"
    assert chamadas["params"]["q_audio"] is None
    assert out[0]["pointer"] == "p.mp3"


def test_popula_beds_seta_bed_file(monkeypatch, tmp_path):
    mp3 = tmp_path / "faixa.mp3"
    mp3.write_bytes(b"x")
    monkeypatch.setattr(banco, "banco_disponivel", lambda: True)
    monkeypatch.setattr(banco, "busca_hibrida",
                        lambda **kw: [{"pointer": str(mp3), "rrf": 0.03}])
    tl = {"era": "1980s", "partes": [
        {"tipo": "score", "clima": "romantic", "mood": "cheesy ballad",
         "ironia": "kitsch", "start": 0.0, "end": 10.0},
        {"tipo": "diegetic", "clima": "joyful", "start": 10.0, "end": 20.0},
    ]}
    banco.popula_beds(tl)
    assert tl["partes"][0]["bed_file"] == str(mp3)
    assert "bed_file" not in tl["partes"][1]          # so_score default


def test_popula_beds_ignora_ponteiro_epidemic(monkeypatch):
    monkeypatch.setattr(banco, "banco_disponivel", lambda: True)
    monkeypatch.setattr(banco, "busca_hibrida",
                        lambda **kw: [{"pointer": "epidemic:abc123", "rrf": 0.03}])
    tl = {"partes": [{"tipo": "score", "clima": "epic", "mood": "big", "start": 0, "end": 9}]}
    banco.popula_beds(tl)
    assert "bed_file" not in tl["partes"][0]          # ponteiro sem áudio local
