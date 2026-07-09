# Regras de APPLY do diretor — comportamento de execução (trilha.py)

NÃO é injetado no prompt do reader (regras_diretor.md é). Estas regras condicionam o
APPLY; implementação rastreada na camada 1.5.

- STOP de música DIEGÉTICA por parada narrativa + gênero fun/divertido/COMÉDIA ->
  slow-down de pitch (toca-discos parando), respeitando os cortes do filme.
  SEM agulha arranhando por enquanto. Gênero sério -> corte limpo, sem wind-down.
  (ditada 2026-07-09; `_stop_diegetico`/`_wind_down` já existem em trilha.py —
  falta condicionar ao gênero: `comico=True` OU clima da parte em
  {comedic, playful, joyful}; e suprimir needle scratch das pontuações por ora)
