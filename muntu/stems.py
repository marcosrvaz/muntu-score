"""Task 9 — manifest de stems: seleciona o stem por PAPEL (+ clima).

O director diz o TIPO do acento (impact/perc/riser); o manifest mapeia papel->arquivo.
Tira o "1 stem repetido em todo corte". Selecao simples e deterministica; variacao
contextual por corte (SFX gerado) e a camada de sound design (ver nota de pesquisa).

manifest.json (em assets/stems/<pack>/): {"stems": [{arquivo, clima, papel}, ...]}
papel = hit | pad | perc | riser

LEGADO (hits nos cortes OFF, decisao 2026-07: estetica trailer): sem consumidor no
pipeline; mantido pra eventual modo "hits" futuro. Testes cobrem o contrato pra
reativacao. Nao expandir sem reativar.
"""
from __future__ import annotations

import json
import os

PAPEL_DE_TIPO = {"impact": "hit", "perc": "perc", "riser": "riser", "pad": "pad"}
STEM_FALLBACK = "hit.wav"


def papel_de_tipo(tipo: str) -> str:
    return PAPEL_DE_TIPO.get(tipo, "hit")


def carrega_manifest(stems_dir: str) -> list[dict]:
    """Lista de stems do manifest.json. [] se o arquivo nao existir."""
    caminho = os.path.join(stems_dir, "manifest.json")
    if not os.path.exists(caminho):
        return []
    with open(caminho, encoding="utf-8") as f:
        return json.load(f).get("stems", [])


def manifest_e_placeholder(stems_dir: str) -> bool:
    """True se o manifest esta ausente ou marcado PLACEHOLDER (stems ainda nao sao reais).

    Nesse caso o pipeline NAO renderiza o beep de assinatura — o foley carrega os cortes e
    o resto fica em silencio. Quando o usuario poe stems reais (edita o `_nota`/arquivos), a
    assinatura (climax + fechamento) volta sozinha.
    """
    caminho = os.path.join(stems_dir, "manifest.json")
    if not os.path.exists(caminho):
        return True
    with open(caminho, encoding="utf-8") as f:
        nota = json.load(f).get("_nota", "")
    return "PLACEHOLDER" in nota.upper()


def escolhe(manifest: list[dict], papel: str, clima: str | None = None) -> str | None:
    """Stem por papel; prefere clima igual. None se nenhum stem tem o papel."""
    cands = [s for s in manifest if s.get("papel") == papel]
    if not cands:
        return None
    if clima:
        por_clima = [s for s in cands if s.get("clima") == clima]
        if por_clima:
            return por_clima[0]["arquivo"]
    return cands[0]["arquivo"]
