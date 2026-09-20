from tabsmith.transcribe import infer_meter


def test_infer_meter_ignores_phantom_downbeats():
    beats = [i * 0.5 for i in range(16)]
    # a phantom downbeat one beat in, then real ones every 4 beats
    assert infer_meter(beats, [0.0, 0.5, 2.0, 4.0, 6.0]) == (4, 0.0)


def test_infer_meter_finds_waltz_and_pickup():
    beats = [i * 0.6 for i in range(18)]
    # downbeats every 3 beats starting one beat in (a pickup beat), one spurious extra
    assert infer_meter(beats, [0.6, 2.4, 4.2, 6.0, 7.8, 8.4]) == (3, 0.6)


def test_infer_meter_without_downbeats_is_4_4():
    assert infer_meter([0.0, 0.5, 1.0, 1.5], []) == (4, 0.0)
