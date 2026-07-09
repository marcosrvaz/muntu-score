"""Prova de ouvido: tag curta vs ensaio no ElevenLabs text-to-SFX.

Isola a hipotese do VLM: manda 2 versoes do MESMO som (tag x paragrafo) pro
gerador, gera 4 mp3, usuario ouve A/B. Nao toca em sfx_map.py. Mesmo dur por par.
"""
from dotenv import load_dotenv
load_dotenv()

from muntu import sfx_gen

OUT = "outputs/prova-ouvido"
DUR = 1.2

PARES = [
    # cena, tag_curta, ensaio_rico
    ("cena1-ambiencia-festa",
     "indoor crowded party hall ambience",
     "large reverberant indoor party hall, warm low crowd hum in the distance, occasional muffled glass clink"),
    ("cena2-foley-lata-chips",
     "hand pops open a foil chips can",
     "a hand grips a cardboard foil chips tube and pops the plastic lid off, short crisp crackle peel"),
]

def main():
    import os
    os.makedirs(OUT, exist_ok=True)
    for cena, tag, ensaio in PARES:
        for rotulo, texto in (("A-tag", tag), ("B-ensaio", ensaio)):
            seg = sfx_gen.gera_sfx(texto, duracao_s=DUR)
            if seg is None:
                print(f"  {cena} {rotulo}: FALHOU")
                continue
            path = f"{OUT}/{cena}-{rotulo}.mp3"
            seg.export(path, format="mp3")
            print(f"  {cena} {rotulo}: OK -> {path}  (texto: {texto!r})")

if __name__ == "__main__":
    main()
