import os
import sys
import types

from muntu import sfx_gen
from muntu.sfx_gen import gera_sfx


# ---- cache corrompido nao pode quebrar o contrato best-effort ----

def test_gera_sfx_cache_corrompido_remove_e_regenera_none(monkeypatch, tmp_path):
    monkeypatch.setattr(sfx_gen, "sfx_disponivel", lambda: True)
    cache_dir = str(tmp_path)
    texto = "vidro quebrando"
    cache_file = sfx_gen._cache_path(texto, sfx_gen.DUR_S, cache_dir)
    os.makedirs(cache_dir, exist_ok=True)
    with open(cache_file, "wb") as f:
        f.write(b"nao e mp3")

    # forca a geracao (apos o cache corrompido) a falhar, sem depender de credencial real
    fake_elevenlabs = types.ModuleType("elevenlabs")

    class ElevenLabsFalho:
        def __init__(self, *a, **k):
            raise RuntimeError("sem credencial valida")

    fake_elevenlabs.ElevenLabs = ElevenLabsFalho
    monkeypatch.setitem(sys.modules, "elevenlabs", fake_elevenlabs)

    resultado = gera_sfx(texto, cache_dir=cache_dir)
    assert resultado is None
    assert not os.path.exists(cache_file)
