from tabsmith.fretboard import BANJO_G, GUITAR, shape_for, shape_position, FretMapper


def test_banjo_positions_respect_fifth_string():
    pos = BANJO_G.positions(69)      # A4
    assert (1, 7) in pos and (2, 10) in pos
    assert (5, 7) in pos, "fifth string nut is at fret 5, so A4 is physical fret 7"
    assert all(not (s == 5 and 0 < f < 5) for s, f in pos)
    assert (5, 2) not in pos
    assert BANJO_G.pitch(5, 7) == 69 and BANJO_G.pitch(5, 0) == 67
    assert BANJO_G.positions(67) == [(1, 5), (2, 8), (3, 12), (4, 17), (5, 0)]


def test_shapes():
    assert shape_for(BANJO_G, "G") == (0, 0, 0, 0, 0)
    assert shape_for(BANJO_G, "C") == (2, 1, 0, 2, 0)
    assert shape_for(BANJO_G, "D7") == (4, 1, 2, 0, 0)
    assert shape_for(GUITAR, "G") == (3, 0, 0, 0, 2, 3)
    assert shape_for(GUITAR, "Am") == (0, 1, 2, 2, 0, -1)
    # unknown chord: moved barre, still voices the right pitch classes
    bb = shape_for(GUITAR, "Bb")
    pcs = {GUITAR.pitch(s + 1, f) % 12 for s, f in enumerate(bb) if f >= 0}
    assert pcs == {10, 2, 5}
    assert shape_position(shape_for(BANJO_G, "A")) == 2


def test_mapper_prefers_open_position_and_stays_close():
    m = FretMapper(BANJO_G)
    out = m.assign([55, 57, 59, 62], anchor=0)   # G3 A3 B3 D4: open-position run
    assert out[0] == (3, 0)
    assert all(BANJO_G.ok(s, f) for s, f in out)
    assert max(f for _, f in out) <= 4
    high = m.assign([67, 69, 71, 74], anchor=0)   # G4 A4 B4 D5 must not ride the fretted fifth string
    assert all(not (s == 5 and f > 0) for s, f in high)


def test_mapper_string_restriction():
    m = FretMapper(GUITAR, strings=(1, 2, 3))
    out = m.assign([64, 67, 71])
    assert all(s in (1, 2, 3) for s, _ in out)
