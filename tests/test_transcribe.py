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


def test_gpu_wait_gives_up_loudly(monkeypatch):
    import pytest

    from tabsmith import transcribe as t

    class Busy:
        def json(self):
            return {"queue_running": [1], "queue_pending": []}
    monkeypatch.setattr(t.requests, "get", lambda *a, **k: Busy())
    monkeypatch.setattr(t.time, "sleep", lambda s: None)
    with pytest.raises(RuntimeError, match="GPU busy"):
        t.gpu_wait(max_wait_s=60, poll_s=30, progress=lambda m: None)


def test_normalise_tempo_fixes_the_octave():
    from tabsmith.transcribe import normalise_tempo
    slow = [i * 1.2 for i in range(10)]            # 50 bpm
    fast = [i * 0.2 for i in range(40)]            # 300 bpm
    ok = [i * 0.5 for i in range(10)]              # 120 bpm
    assert len(normalise_tempo(slow)) == 19 and abs(normalise_tempo(slow)[1] - 0.6) < 1e-9
    assert len(normalise_tempo(fast)) == 20
    assert normalise_tempo(ok) == ok
    # downbeats every 4 slow beats still read as 4/4 after doubling
    assert infer_meter(normalise_tempo(slow), [0.0, 4.8, 9.6]) == (4, 0.0)
