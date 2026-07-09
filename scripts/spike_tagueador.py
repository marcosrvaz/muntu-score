"""Spike do crux (spec §2.7): taguear 3-4 ads reais pro usuário julgar de ouvido/olho.

Uso: python scripts/spike_tagueador.py <ad1.mp4> <ad2.mp4> ...
Saída: outputs/spike_tags/<stem>.json por ad + outputs/spike_tags/RELATORIO.md
Julgamento (usuário): o modelo leu ironia/cultura/traço de voz FINO? Se não, calibrar
prompt e re-rodar; se nem calibrado ler, o banco (WS-C) não deve ser populado em massa.
"""
import json
import os
import sys

from muntu import tagueador


def main(paths):
    os.makedirs("outputs/spike_tags", exist_ok=True)
    linhas = ["# Spike tagueador — julgamento de registro fino\n"]
    for p in paths:
        r = tagueador.tagueia_ad(p)
        stem = os.path.splitext(os.path.basename(p))[0]
        dst = f"outputs/spike_tags/{stem}.json"
        with open(dst, "w", encoding="utf-8") as f:
            json.dump(r, f, ensure_ascii=False, indent=2)
        linhas.append(f"\n## {stem}\n")
        for m in r["musica"]:
            linhas.append(f"- musica [{m.get('span', '')}]: {m['registro']} | ironia={m['ironia']}"
                          f" | cultura={m['cultura'] or '—'} | instr={m['instrumentacao']}")
        vo = r["vo"]
        linhas.append(f"- vo: {vo}" if vo else "- vo: (sem locução)")
        linhas.append(f"- sfx: {r['sfx']}")
        print(f"[spike] {stem} -> {dst}")
    with open("outputs/spike_tags/RELATORIO.md", "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))
    print("[spike] relatório: outputs/spike_tags/RELATORIO.md")


if __name__ == "__main__":
    main(sys.argv[1:])
