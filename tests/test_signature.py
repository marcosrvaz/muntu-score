from muntu.signature import placement_plan


def test_placement_at_cuts():
    cuts = [1.0, 2.5, 4.0]
    plan = placement_plan(cuts, duracao=5.0)
    assert [p["t"] for p in plan] == cuts
    assert all(p["stem"] == "hit.wav" for p in plan)
