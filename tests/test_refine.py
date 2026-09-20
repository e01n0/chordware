import json
from tabsmith.leadsheet import LeadSheet, MelodyNote, Chord
from tabsmith.arrange import arrange, check_invariants
from tabsmith.refine import parse_reply, apply_refinement, build_prompt, refine


def sheet():
    melody = [MelodyNote(t, 0.5, p) for t, p in [(0, 62), (0.5, 64), (1, 67), (1.5, 69), (2, 67), (3, 62)]]
    return LeadSheet("R", "t", 120, (4, 4), "G", "major", 0, 2, melody, [Chord(0, 0, "G"), Chord(1, 0, "D7")], [])


def test_parse_reply_rejects_unknown_pattern():
    assert parse_reply(json.dumps({"sections": [], "pattern_by_section": {"A": "nope"}, "ornaments": [], "notes": ""})) is None
    assert parse_reply("not json") is None
    r = parse_reply(json.dumps({"sections": [{"bar": 0, "label": "A"}], "pattern_by_section": {"A": "foggy"},
                                "ornaments": [], "notes": "ok"}))
    assert r.patterns == {"A": "foggy"}


def test_apply_refinement_validates_ornaments():
    arr = arrange(sheet(), "banjo", "scruggs")
    ref = parse_reply(json.dumps({
        "sections": [{"bar": 0, "label": "A"}], "pattern_by_section": {"A": "forward"},
        "ornaments": [{"bar": 0, "beat": 0.0, "kind": "h", "from": 0, "to": 2},      # D open 1st to E fret 2: valid
                      {"bar": 0, "beat": 1.0, "kind": "s", "from": 0, "to": 9}],     # span too big: dropped
        "notes": ""}))
    out = apply_refinement(arr, ref)
    check_invariants(out)
    techs = [(n.t, n.tech) for n in out.notes if n.tech]
    assert (0.0, "h") in techs and not any(t == 1.0 for t, _ in techs)
    assert out.sheet.sections == [{"bar": 0, "label": "A"}]


def test_prompt_mentions_rolls_and_chords():
    p = build_prompt(sheet(), "tab", "banjo", "scruggs")
    assert "forward_backward" in p and "D7" in p and "JSON" in p


def test_refine_survives_ollama_down():
    assert refine(sheet(), "tab", "banjo", "scruggs", url="http://127.0.0.1:1") is None
