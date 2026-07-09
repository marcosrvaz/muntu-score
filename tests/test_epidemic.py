from muntu import epidemic


def test_indisponivel_sem_key(monkeypatch):
    monkeypatch.delenv("EPIDEMIC_API_KEY", raising=False)
    assert epidemic.epidemic_disponivel() is False
    # todas as portas caem em vazio/None sem tocar rede
    assert epidemic.busca("romantic") == []
    assert epidemic.baixa_faixa("abc") is None
    assert epidemic.bed_para_clima("romantic") is None


def test_disponivel_com_key(monkeypatch):
    monkeypatch.setenv("EPIDEMIC_API_KEY", "epidemic_live_x")
    assert epidemic.epidemic_disponivel() is True


def test_busca_best_effort(monkeypatch):
    # erro de rede -> [] (parte cai em A, nao quebra)
    monkeypatch.setattr(epidemic, "epidemic_disponivel", lambda: True)

    def boom(_path, _params):
        raise RuntimeError("boom")

    monkeypatch.setattr(epidemic, "_get_tracks", boom)
    assert epidemic.busca("romantic") == []


def test_term_traduz_pt_en():
    assert epidemic._term("comico e leve") == "quirky e leve"       # traduz palavra PT
    assert epidemic._term("uplifting corporate energy") == "uplifting corporate energy"  # EN passa
    assert epidemic._term("  ROMANTICO  ") == "romantic"            # normaliza + traduz
    assert epidemic._term("festa dancante") == "party dance"
    assert epidemic._term(None) is None
    assert epidemic._term("   ") is None


def test_clima_casa_os_3_eixos():
    # biblioteca de climas do muntu (mood.MOODS) casa com o mapa de composicao nos 3 eixos:
    # mode->mood, arousal->BPM, instrumentacao->genre. Ancorado na pesquisa.
    from muntu import mood
    assert epidemic.CLIMA_EPIDEMIC["romantic"] == "romantic"
    assert epidemic.CLIMA_EPIDEMIC["melancholic"] == "sad"
    assert epidemic.CLIMA_EPIDEMIC["energetic"] == "running"    # cinetica, nao euphoric (pesquisa)
    assert epidemic.CLIMA_BPM["melancholic"] == (60, 80)        # tabela de convencao
    assert epidemic.CLIMA_GENERO["epic"] == "classical"         # brass/orquestral -> classical
    # todo clima do reader casa em mood + alvos sao ids VALIDOS do Epidemic
    for clima in mood.MOODS:
        assert clima in epidemic.CLIMA_EPIDEMIC, f"clima '{clima}' sem mood"
        assert epidemic.CLIMA_EPIDEMIC[clima] in epidemic.MOODS_VALIDOS
    # defaults por clima = top-level (fallback seguro); GENERO_EPIDEMIC pode ter granular
    for clima, gid in epidemic.CLIMA_GENERO.items():
        assert gid in epidemic.GENEROS_VALIDOS, f"genero default '{gid}' nao e top-level"
    # register que nomeia estilo alcanca subgenero granular (calibrado no A/B)
    assert epidemic.GENERO_EPIDEMIC["ballad"] == "ballad"
    assert epidemic.GENERO_EPIDEMIC["arena"] == "arena-rock"
    assert epidemic.GENERO_EPIDEMIC["sax"] == "smooth-jazz"


def test_busca_clima_casa_3_eixos(monkeypatch):
    # clima -> 1a tentativa = mood + genre + BPM (os 3 eixos do mapa de composicao)
    monkeypatch.setattr(epidemic, "epidemic_disponivel", lambda: True)
    chamadas = []
    monkeypatch.setattr(epidemic, "_get_tracks",
                        lambda path, params: chamadas.append((path, params)) or [{"id": "t1"}])
    out = epidemic.busca(clima="melancholic")
    assert out == [{"id": "t1"}]
    p = chamadas[0][1]
    assert p["mood"] == "sad" and p["genre"] == "solo-piano"    # mode + instrumentacao
    assert p["bpmMin"] == 60 and p["bpmMax"] == 80             # arousal (banda do clima)


def test_busca_register_vence_genero_default(monkeypatch):
    # register que nomeia genero vence o default do clima
    monkeypatch.setattr(epidemic, "epidemic_disponivel", lambda: True)
    chamadas = []
    monkeypatch.setattr(epidemic, "_get_tracks",
                        lambda path, params: chamadas.append((path, params)) or [{"id": "t1"}])
    epidemic.busca(clima="epic", register="surf rock")         # epic default=classical
    assert chamadas[0][1]["genre"] == "surf-rock"              # register vence (granular calibrado)


def test_busca_register_usa_term(monkeypatch):
    # sem clima mapeavel, register free-text -> /v0/tracks/search?term=
    monkeypatch.setattr(epidemic, "epidemic_disponivel", lambda: True)
    chamadas = []
    monkeypatch.setattr(epidemic, "_get_tracks",
                        lambda path, params: chamadas.append((path, params)) or [{"id": "t2"}])
    out = epidemic.busca(clima=None, register="80s cheesy sax")
    assert out == [{"id": "t2"}]
    assert chamadas[0][0] == "/v0/tracks/search"
    assert chamadas[0][1]["term"] == "80s cheesy sax"


def test_busca_fallback_search_vazio(monkeypatch):
    # mood= vazio -> cai no browse /v0/tracks -> acha
    monkeypatch.setattr(epidemic, "epidemic_disponivel", lambda: True)
    monkeypatch.setattr(epidemic, "_get_tracks",
                        lambda path, params: [] if "mood" in params else [{"id": "t3"}])
    assert epidemic.busca(clima="epic") == [{"id": "t3"}]


def test_busca_fallback_http_error_degrada(monkeypatch):
    # 4xx numa tentativa -> tenta a proxima (nao retorna [] na hora)
    monkeypatch.setattr(epidemic, "epidemic_disponivel", lambda: True)
    import httpx

    calls = {"n": 0}

    def fake(path, params):
        calls["n"] += 1
        if calls["n"] == 1:                              # 1a tentativa (mood+genre+bpm) -> 400
            req = httpx.Request("GET", "http://x")
            raise httpx.HTTPStatusError("bad", request=req,
                                        response=httpx.Response(400, request=req))
        return [{"id": "t3"}]

    monkeypatch.setattr(epidemic, "_get_tracks", fake)
    assert epidemic.busca(clima="epic") == [{"id": "t3"}]


def test_baixa_faixa_usa_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(epidemic, "epidemic_disponivel", lambda: True)
    pronto = tmp_path / "0f88e2c3b1a4d5e6.mp3"      # nome nao importa: forcamos existencia
    # simula cache-hit: cria o arquivo que o hash produziria
    import hashlib
    h = hashlib.sha1("tid|normal".encode()).hexdigest()[:16]
    (tmp_path / f"{h}.mp3").write_bytes(b"ID3fake")
    called = {"n": 0}

    def nao_deve_chamar(*a, **k):
        called["n"] += 1
        return "http://x"

    monkeypatch.setattr(epidemic, "_url_download", nao_deve_chamar)
    out = epidemic.baixa_faixa("tid", cache_dir=str(tmp_path))
    assert out == str(tmp_path / f"{h}.mp3")
    assert called["n"] == 0                          # cache-hit: nao resolve URL


def test_baixa_faixa_sem_url(monkeypatch, tmp_path):
    monkeypatch.setattr(epidemic, "epidemic_disponivel", lambda: True)
    monkeypatch.setattr(epidemic, "_url_download", lambda tid, q=None: None)
    assert epidemic.baixa_faixa("tid", cache_dir=str(tmp_path)) is None


def test_popula_beds_seta_por_clima(monkeypatch):
    monkeypatch.setattr(epidemic, "epidemic_disponivel", lambda: True)
    monkeypatch.setattr(epidemic, "bed_para_clima",
                        lambda clima, register=None, bpm=None, cache_dir=None: f"/beds/{clima}.mp3")
    tl = {"partes": [
        {"tipo": "score", "clima": "romantic", "mood": "80s sax"},
        {"tipo": "diegetic", "clima": "joyful"},       # so_score -> pulada
        {"tipo": "score", "clima": "tense", "bed_file": "/ja/existe.mp3"},  # nao sobrescreve
    ]}
    out = epidemic.popula_beds(tl)
    assert out["partes"][0]["bed_file"] == "/beds/romantic.mp3"
    assert "bed_file" not in out["partes"][1]         # diegetica pulada
    assert out["partes"][2]["bed_file"] == "/ja/existe.mp3"  # PIN manual respeitado


def test_popula_beds_indisponivel_noop(monkeypatch):
    monkeypatch.setattr(epidemic, "epidemic_disponivel", lambda: False)
    tl = {"partes": [{"tipo": "score", "clima": "epic"}]}
    out = epidemic.popula_beds(tl)
    assert "bed_file" not in out["partes"][0]         # sem key -> timeline intacta (cai em A)


def test_baixa_faixa_segue_redirects(monkeypatch, tmp_path):
    # httpx NAO segue redirect por default (diferente de requests); CDN costuma dar 302
    monkeypatch.setattr(epidemic, "epidemic_disponivel", lambda: True)
    monkeypatch.setattr(epidemic, "_url_download", lambda tid, q=None: "http://cdn/x.mp3")
    import httpx

    captured = {}

    class FakeResp:
        def raise_for_status(self):
            pass

        def iter_bytes(self):
            yield b"ID3fake"

    class FakeStream:
        def __init__(self, method, url, **kw):
            captured.update(kw)

        def __enter__(self):
            return FakeResp()

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(httpx, "stream", FakeStream)
    out = epidemic.baixa_faixa("tid", cache_dir=str(tmp_path))
    assert out is not None
    assert captured.get("follow_redirects") is True


def test_baixa_faixa_escrita_atomica(monkeypatch, tmp_path):
    # processo concorrente nao pode ver o destino final truncado durante a escrita; falha
    # no meio do stream -> destino final NAO existe (nem truncado), .part removido
    monkeypatch.setattr(epidemic, "epidemic_disponivel", lambda: True)
    monkeypatch.setattr(epidemic, "_url_download", lambda tid, q=None: "http://cdn/x.mp3")
    import hashlib
    import httpx

    h = hashlib.sha1("tid|normal".encode()).hexdigest()[:16]
    destino = tmp_path / f"{h}.mp3"
    visto_durante_escrita = {}

    class FakeResp:
        def raise_for_status(self):
            pass

        def iter_bytes(self):
            yield b"parte1"
            visto_durante_escrita["existe"] = destino.exists()  # o que um leitor concorrente veria
            raise RuntimeError("conexao caiu")

    class FakeStream:
        def __init__(self, method, url, **kw):
            pass

        def __enter__(self):
            return FakeResp()

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(httpx, "stream", FakeStream)
    out = epidemic.baixa_faixa("tid", cache_dir=str(tmp_path))
    assert out is None
    assert visto_durante_escrita["existe"] is False   # destino final nunca visivel truncado
    assert not destino.exists()
    assert not (tmp_path / f"{h}.mp3.part").exists()


def test_genero_compostos_por_espaco_ou_hifen():
    # bug: "synth-pop" (hifen) nao e chave direta e caia em electronic via split; "hard rock"
    # (espaco) virava rock antes de alcancar a chave composta "hard-rock"
    assert epidemic._genero("synth-pop") == "synth-pop"
    assert epidemic._genero("synth pop") == "synth-pop"
    assert epidemic._genero("hard rock") == "hard-rock"
    assert epidemic._genero("hard-rock") == "hard-rock"
    # casos existentes intactos
    assert epidemic._genero("surf rock") == "surf-rock"
    assert epidemic._genero("80s cheesy sax") == "smooth-jazz"
    assert epidemic._genero("indie-pop band") == "indie-pop"
