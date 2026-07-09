import os

from muntu import foley
from muntu.foley import (
    foley_disponivel, _janela, seleciona_assinatura, _cache_key, gera_foley_de_corte,
)


# ---- gating ----

def test_foley_indisponivel_sem_token(monkeypatch):
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    assert foley_disponivel() is False


def test_gera_foley_sem_token_devolve_none(monkeypatch):
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    assert gera_foley_de_corte("qualquer.mp4", 3.0, 16.0) is None


# ---- janela (pura) ----

def test_janela_ao_redor_do_corte():
    assert _janela(8.0, 16.0, pre=1.25, pos=1.25) == (6.75, 9.25)


def test_janela_presa_nas_bordas():
    assert _janela(0.5, 16.0, pre=1.25, pos=1.25) == (0.0, 1.75)     # inicio nao passa de 0
    assert _janela(15.5, 16.0, pre=1.25, pos=1.25) == (14.25, 16.0)  # fim nao passa da duracao


# ---- hierarquia assinatura vs foley (pura) ----

def _acentos():
    # tipo/t_audio/t_video como o director produz
    return [
        {"t_video": 1.6, "t_audio": 1.6, "tipo": "perc"},
        {"t_video": 6.8, "t_audio": 6.8, "tipo": "impact"},
        {"t_video": 11.9, "t_audio": 11.9, "tipo": "impact"},
        {"t_video": 15.8, "t_audio": 15.8, "tipo": "perc"},
    ]


def test_assinatura_climax_e_fechamento_sem_vlm():
    acentos = _acentos()
    idx = seleciona_assinatura(acentos, cenas=None)
    # fechamento = ultimo (i=3); climax sem VLM = impact mais tardio (i=2)
    assert idx == {2, 3}


def test_assinatura_climax_pela_energia_com_vlm():
    acentos = _acentos()
    # pico de energia na 1a metade (cena do corte i=1) -> climax vai pra la
    cenas = [{"start": 0, "end": 9, "energia": 5}, {"start": 9, "end": 16, "energia": 2}]
    idx = seleciona_assinatura(acentos, cenas=cenas)
    assert 1 in idx           # climax = corte na cena de maior energia
    assert 3 in idx           # fechamento = ultimo


def test_assinatura_vazio_sem_acentos():
    assert seleciona_assinatura([], cenas=None) == set()


# ---- cache key (pura, deterministica) ----

def test_cache_key_muda_com_corte():
    a = _cache_key("v.mp4", 3.0)
    b = _cache_key("v.mp4", 6.0)
    assert a != b
    assert _cache_key("v.mp4", 3.0) == a      # deterministica


# ---- cache corrompido nao pode quebrar o contrato best-effort ----

def test_gera_foley_cache_corrompido_remove_e_regenera_none(monkeypatch, tmp_path):
    monkeypatch.setattr(foley, "foley_disponivel", lambda: True)
    cache_dir = str(tmp_path)
    video_path, corte, prompt = "v.mp4", 3.0, ""
    cache_file = foley._cache_path(foley._cache_key(video_path, corte, prompt), cache_dir)
    os.makedirs(cache_dir, exist_ok=True)
    with open(cache_file, "wb") as f:
        f.write(b"nao e mp3")

    def _falha(*a, **k):
        raise RuntimeError("sem ffmpeg")
    monkeypatch.setattr(foley, "_extrai_janela", _falha)

    resultado = gera_foley_de_corte(video_path, corte, 16.0, cache_dir=cache_dir)
    assert resultado is None
    assert not os.path.exists(cache_file)
