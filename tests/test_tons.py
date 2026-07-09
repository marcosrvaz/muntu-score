from pydub.generators import Sine

from muntu import tons


def _acorde(*freqs, dur_ms=3000):
    segs = [Sine(f).to_audio_segment(duration=dur_ms) for f in freqs]
    out = segs[0]
    for s in segs[1:]:
        out = out.overlay(s)
    return out


def test_semitonos_matematica():
    assert tons.semitonos("C major", "E major") == 4
    assert tons.semitonos("C major", "G major") == -5     # menor distancia (-5, nao +7)
    assert tons.semitonos("G major", "C major") == 5      # menor distancia (+5, nao -7)
    assert tons.semitonos("A minor", "C major") == 3      # tonica relativa
    assert tons.semitonos("C major", "C major") == 0


def test_semitonos_invalido():
    assert tons.semitonos(None, "C major") == 0
    assert tons.semitonos("C major", None) == 0
    assert tons.semitonos("xx yy", "C major") == 0        # parse falha -> 0


def test_semitonos_bemol_equivale_ao_sustenido_enarmonico():
    # "Db major" tem que transpor igual "C# major" (mesma nota, grafia diferente)
    assert tons.semitonos("Db major", "C major") == tons.semitonos("C# major", "C major")
    assert tons.semitonos("C major", "Eb major") == tons.semitonos("C major", "D# major")
    assert tons.semitonos("Gb major", "Ab major") == tons.semitonos("F# major", "G# major")
    assert tons.semitonos("Bb major", "C major") == tons.semitonos("A# major", "C major")


def test_detecta_tom_acorde_conhecido():
    # acorde maior claro: C-E-G (C major)
    seg = _acorde(261.63, 329.63, 392.00)
    assert tons.detecta_tom(seg) == "C major"


def test_transpor_zero_eh_identidade():
    seg = _acorde(261.63, 329.63, 392.00, dur_ms=1000)
    assert tons.transpor(seg, 0) is seg


def test_transpor_preserva_duracao_e_muda_tom():
    seg = _acorde(261.63, 329.63, 392.00)                 # C major
    t = tons.transpor(seg, 2)                             # -> D major
    assert len(t) == len(seg)                             # pitch-shift preserva tempo
    assert tons.detecta_tom(t) == "D major"


def test_alinha_tom_transpoe_pro_alvo():
    # seg em D major, alvo C major -> deve virar C major (-2 semitons)
    seg = _acorde(293.66, 369.99, 440.00)                 # D-F#-A = D major
    alinhado = tons.alinha_tom(seg, "C major")
    assert tons.detecta_tom(alinhado) == "C major"


def test_alinha_tom_sem_alvo_nao_transpoe():
    seg = _acorde(261.63, 329.63, 392.00)
    assert tons.alinha_tom(seg, None) is seg
