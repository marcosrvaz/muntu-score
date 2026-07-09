import io
import os

from pydub import AudioSegment

from muntu import musica
from muntu.musica import _cache_path, musica_disponivel, gera_musica


def test_cache_path_deterministico():
    a = _cache_path("stability|warm bed|30.0", "outputs/cache")
    b = _cache_path("stability|warm bed|30.0", "outputs/cache")
    c = _cache_path("stability|outro|30.0", "outputs/cache")
    assert a == b and a != c


def test_cama_indisponivel_sem_credencial(monkeypatch):
    monkeypatch.delenv("STABILITY_API_KEY", raising=False)
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    assert musica_disponivel("stability") is False
    assert musica_disponivel("elevenlabs") is False
    assert musica_disponivel("provedor_zzz") is False


def test_gera_musica_sem_credencial_e_sem_cache_levanta(monkeypatch, tmp_path):
    monkeypatch.delenv("STABILITY_API_KEY", raising=False)
    try:
        gera_musica("qualquer", 8.0, provider="stability", cache_dir=str(tmp_path))
        assert False, "deveria ter levantado RuntimeError"
    except RuntimeError as e:
        assert "indisponivel" in str(e)


def test_gera_musica_usa_cache_sem_api(monkeypatch, tmp_path):
    # pre-popula o cache -> nao chama API mesmo sem credencial
    monkeypatch.delenv("STABILITY_API_KEY", raising=False)
    prompt, dur, prov = "warm bed, 100 BPM", 8.0, "stability"
    chave = f"{prov}|{prompt}|{round(dur, 1)}"
    cache_file = musica._cache_path(chave, str(tmp_path))
    AudioSegment.silent(duration=int(dur * 1000)).export(cache_file, format="mp3")

    seg = gera_musica(prompt, dur, provider=prov, cache_dir=str(tmp_path))
    assert isinstance(seg, AudioSegment)
    assert len(seg) >= int(dur * 1000) - 100


def test_provider_default_e_elevenlabs():
    # default em TUDO (composition_plan/arco so existe no ElevenLabs — ver director.py)
    assert musica.DEFAULT_PROVIDER == "elevenlabs"


def test_sugestao_de_plano_extrai_do_erro_tos():
    from muntu.musica import _sugestao_de_plano

    class ErroToS(Exception):
        body = {"detail": {"status": "bad_composition_plan",
                           "data": {"composition_plan_suggestion": {"sections": []}}}}

    class ErroOutro(Exception):
        body = {"detail": {"status": "quota_exceeded"}}

    assert _sugestao_de_plano(ErroToS()) == {"sections": []}
    assert _sugestao_de_plano(ErroOutro()) is None      # outro 400: nao retry
    assert _sugestao_de_plano(Exception("sem body")) is None


def test_reconcilia_chunks_devolve_estilos_e_espelha_cauda():
    from muntu.musica import _reconcilia_chunks

    class Chunk:
        def __init__(self, estilos):
            self.positive_styles = estilos

    class Plan:
        def __init__(self, chunks):
            self.chunks = chunks

    # create() moveu o payoff (sax solo) pro chunk da Cauda — reconcilia devolve
    cp = {"sections": [
        {"section_name": "Apice", "positive_local_styles": ["sax solo", "violins"]},
        {"section_name": "Cauda", "positive_local_styles": ["sax solo", "violins"]}]}
    plan = Plan([Chunk(["80 BPM"]), Chunk(["sax solo", "maximum peak"])])
    out = _reconcilia_chunks(plan, cp)
    assert "sax solo" in out.chunks[0].positive_styles     # payoff de volta no Apice
    assert "violins" in out.chunks[0].positive_styles
    assert out.chunks[1].positive_styles == out.chunks[0].positive_styles  # Cauda = espelho


def test_reconcilia_chunks_len_diferente_nao_mexe():
    from muntu.musica import _reconcilia_chunks

    class Plan:
        chunks = []
    cp = {"sections": [{"section_name": "Build", "positive_local_styles": ["x"]}]}
    assert _reconcilia_chunks(Plan(), cp) is not None      # best-effort, sem crash


def test_gera_musica_bytes_invalidos_nao_cacheia(monkeypatch, tmp_path):
    # stream truncado/corpo de erro com 200 nao pode poluir o cache
    monkeypatch.setattr(musica, "musica_disponivel", lambda p=None: True)
    monkeypatch.setattr(musica, "_gera_stability", lambda prompt, duracao: b"lixo")

    prompt, dur, prov = "prompt invalido", 8.0, "stability"
    try:
        gera_musica(prompt, dur, provider=prov, cache_dir=str(tmp_path))
        assert False, "deveria ter levantado"
    except Exception:
        pass

    chave = f"{prov}|{prompt}|{round(dur, 1)}"
    cache_file = musica._cache_path(chave, str(tmp_path))
    assert not os.path.exists(cache_file)


def test_gera_musica_cache_corrompido_regenera(monkeypatch, tmp_path):
    # cache envenenado de uma run anterior nao pode derrubar a run seguinte
    prompt, dur, prov = "prompt cache ruim", 8.0, "stability"
    chave = f"{prov}|{prompt}|{round(dur, 1)}"
    cache_file = musica._cache_path(chave, str(tmp_path))
    os.makedirs(str(tmp_path), exist_ok=True)
    with open(cache_file, "wb") as f:
        f.write(b"lixo")

    buf = io.BytesIO()
    AudioSegment.silent(duration=int(dur * 1000)).export(buf, format="mp3")
    valido = buf.getvalue()

    monkeypatch.setattr(musica, "musica_disponivel", lambda p=None: True)
    monkeypatch.setattr(musica, "_gera_stability", lambda prompt, duracao: valido)

    seg = gera_musica(prompt, dur, provider=prov, cache_dir=str(tmp_path))
    assert isinstance(seg, AudioSegment)
    assert len(seg) >= int(dur * 1000) - 100


# ---- retry transiente (timeout/5xx) na chamada ElevenLabs ----

def test_gera_elevenlabs_retry_transiente_5xx_retorna_audio(monkeypatch):
    import sys
    import types

    from muntu.musica import _gera_elevenlabs

    chamadas = []

    class Erro503(Exception):
        status_code = 503

    class FakeMusic:
        @staticmethod
        def compose(**kwargs):
            chamadas.append(kwargs)
            if len(chamadas) == 1:
                raise Erro503("indisponivel")
            return b"audio-ok"

    class FakeClient:
        def __init__(self, *a, **k):
            self.music = FakeMusic()

    fake_elevenlabs = types.ModuleType("elevenlabs")
    fake_elevenlabs.ElevenLabs = FakeClient
    monkeypatch.setitem(sys.modules, "elevenlabs", fake_elevenlabs)

    audio = _gera_elevenlabs("prompt qualquer", 8.0)
    assert audio == b"audio-ok"
    assert len(chamadas) == 2          # 1a falhou (transiente), 2a retry funcionou


def test_gera_elevenlabs_nao_retenta_erro_nao_transiente(monkeypatch):
    import sys
    import types

    from muntu.musica import _gera_elevenlabs

    chamadas = []

    class Erro401(Exception):
        status_code = 401

    class FakeMusic:
        @staticmethod
        def compose(**kwargs):
            chamadas.append(kwargs)
            raise Erro401("nao autorizado")

    class FakeClient:
        def __init__(self, *a, **k):
            self.music = FakeMusic()

    fake_elevenlabs = types.ModuleType("elevenlabs")
    fake_elevenlabs.ElevenLabs = FakeClient
    monkeypatch.setitem(sys.modules, "elevenlabs", fake_elevenlabs)

    try:
        _gera_elevenlabs("prompt qualquer", 8.0)
        assert False, "deveria ter propagado Erro401"
    except Erro401:
        pass
    assert len(chamadas) == 1          # 401 nao e transiente: 1 chamada so


def test_com_retry_transiente_retenta_em_timeout_httpx():
    import httpx

    from muntu.musica import _com_retry_transiente

    chamadas = []

    def fn():
        chamadas.append(1)
        if len(chamadas) == 1:
            raise httpx.TimeoutException("timeout")
        return "ok"

    assert _com_retry_transiente(fn, "teste") == "ok"
    assert len(chamadas) == 2
