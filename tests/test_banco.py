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
