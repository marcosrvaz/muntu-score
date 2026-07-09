import io
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


# ---- retry transiente (timeout/5xx) na chamada ElevenLabs ----

def test_gera_sfx_retry_transiente_5xx_retorna_audio(monkeypatch, tmp_path):
    from pydub import AudioSegment

    monkeypatch.setattr(sfx_gen, "sfx_disponivel", lambda: True)
    cache_dir = str(tmp_path)
    texto = "vidro quebrando"

    buf = io.BytesIO()
    AudioSegment.silent(duration=int(sfx_gen.DUR_S * 1000)).export(buf, format="mp3")
    valido = buf.getvalue()

    chamadas = []

    class Erro503(Exception):
        status_code = 503

    class FakeSFX:
        @staticmethod
        def convert(**kwargs):
            chamadas.append(kwargs)
            if len(chamadas) == 1:
                raise Erro503("indisponivel")
            return valido

    class FakeClient:
        def __init__(self, *a, **k):
            self.text_to_sound_effects = FakeSFX()

    fake_elevenlabs = types.ModuleType("elevenlabs")
    fake_elevenlabs.ElevenLabs = FakeClient
    monkeypatch.setitem(sys.modules, "elevenlabs", fake_elevenlabs)

    resultado = gera_sfx(texto, cache_dir=cache_dir)
    assert resultado is not None
    assert len(chamadas) == 2          # 1a falhou (transiente), 2a retry funcionou


def test_gera_sfx_nao_retenta_erro_nao_transiente(monkeypatch, tmp_path):
    monkeypatch.setattr(sfx_gen, "sfx_disponivel", lambda: True)
    cache_dir = str(tmp_path)
    texto = "vidro quebrando"

    chamadas = []

    class Erro401(Exception):
        status_code = 401

    class FakeSFX:
        @staticmethod
        def convert(**kwargs):
            chamadas.append(kwargs)
            raise Erro401("nao autorizado")

    class FakeClient:
        def __init__(self, *a, **k):
            self.text_to_sound_effects = FakeSFX()

    fake_elevenlabs = types.ModuleType("elevenlabs")
    fake_elevenlabs.ElevenLabs = FakeClient
    monkeypatch.setitem(sys.modules, "elevenlabs", fake_elevenlabs)

    resultado = gera_sfx(texto, cache_dir=cache_dir)
    assert resultado is None           # cai no except best-effort
    assert len(chamadas) == 1          # 401 nao e transiente: 1 chamada so
