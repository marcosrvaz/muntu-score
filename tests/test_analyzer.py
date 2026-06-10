from muntu.analyzer import analyze


def test_analyze_returns_brief():
    brief = analyze("assets/sample.mp4")
    assert brief["duracao"] > 0
    assert isinstance(brief["cortes"], list)
    # cortes em ordem crescente, dentro da duracao
    assert brief["cortes"] == sorted(brief["cortes"])
    assert all(0 <= t <= brief["duracao"] for t in brief["cortes"])
