from muntu.stems import papel_de_tipo, carrega_manifest, escolhe

MANIFEST = [
    {"arquivo": "kick.wav", "clima": "energetico", "papel": "hit"},
    {"arquivo": "thud.wav", "clima": "calmo", "papel": "hit"},
    {"arquivo": "shk.wav", "clima": "sofisticado", "papel": "perc"},
    {"arquivo": "swell.wav", "clima": "calmo", "papel": "riser"},
]


def test_papel_de_tipo():
    assert papel_de_tipo("impact") == "hit"
    assert papel_de_tipo("perc") == "perc"
    assert papel_de_tipo("riser") == "riser"
    assert papel_de_tipo("desconhecido") == "hit"      # fallback


def test_escolhe_por_papel():
    assert escolhe(MANIFEST, "perc") == "shk.wav"
    assert escolhe(MANIFEST, "riser") == "swell.wav"


def test_escolhe_prefere_clima():
    # papel hit tem 2 stems; clima calmo desempata pro thud
    assert escolhe(MANIFEST, "hit", clima="calmo") == "thud.wav"
    assert escolhe(MANIFEST, "hit", clima="energetico") == "kick.wav"


def test_escolhe_clima_sem_match_cai_no_primeiro_do_papel():
    assert escolhe(MANIFEST, "hit", clima="inexistente") == "kick.wav"


def test_escolhe_papel_inexistente_none():
    assert escolhe(MANIFEST, "pad") is None


def test_carrega_manifest_scaffold_real():
    stems = carrega_manifest("assets/stems/default")
    papeis = {s["papel"] for s in stems}
    assert {"hit", "perc", "riser"} <= papeis


def test_carrega_manifest_ausente_vazio(tmp_path):
    assert carrega_manifest(str(tmp_path)) == []
