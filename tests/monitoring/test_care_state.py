from datetime import datetime, timedelta

from monitoring.care_state import CareState
from monitoring.nurse_observer import EMPTY_OBSERVATION

T0 = datetime(2026, 1, 1, 12, 0, 0)


def obs(**kw):
    return {**EMPTY_OBSERVATION, **kw}


def kinds(events):
    return {e.kind for e in events}


def test_quiet_room_raises_nothing():
    state = CareState()
    assert state.update(obs(person_present=True, posture="sitting", motion="slow"), now=T0) == []


def test_witnessed_fall_is_critical_immediately():
    events = CareState().update(
        obs(person_present=True, fall_in_progress=True), now=T0
    )
    assert "fall_event" in kinds(events)
    assert all(e.level == "CRITICAL" for e in events if e.kind == "fall_event")


def test_smoke_is_critical():
    events = CareState().update(obs(visible_smoke_or_flame=True), now=T0)
    assert "fire" in kinds(events)


def test_stove_left_on_alerts_only_after_threshold():
    state = CareState(unattended_heat_s=60)
    on = [{"name": "stove", "state": "on"}]
    state.update(obs(person_present=True, appliances=on), now=T0)
    early = state.update(obs(person_present=False, appliances=on), now=T0 + timedelta(seconds=30))
    late = state.update(obs(person_present=False, appliances=on), now=T0 + timedelta(seconds=90))
    assert not any(k.startswith("unattended_heat") for k in kinds(early))
    assert "unattended_heat_stove" in kinds(late)


def test_explicit_off_clears_the_heat_timer():
    state = CareState(unattended_heat_s=10)
    state.update(obs(person_present=True, appliances=[{"name": "stove", "state": "on"}]), now=T0)
    state.update(obs(person_present=True, appliances=[{"name": "stove", "state": "off"}]), now=T0 + timedelta(seconds=5))
    events = state.update(obs(person_present=False), now=T0 + timedelta(seconds=60))
    assert not any(k.startswith("unattended_heat") for k in kinds(events))


def test_same_non_critical_alert_is_muted_within_cooldown():
    state = CareState(unattended_heat_s=0, cooldown_s=300)
    on = [{"name": "stove", "state": "on"}]
    state.update(obs(person_present=True, appliances=on), now=T0)
    first = state.update(obs(person_present=False, appliances=on), now=T0 + timedelta(seconds=1))
    second = state.update(obs(person_present=False, appliances=on), now=T0 + timedelta(seconds=2))
    assert "unattended_heat_stove" in kinds(first)
    assert "unattended_heat_stove" not in kinds(second)


def _run(state, *steps):
    found = set()
    for secs, o in steps:
        found |= kinds(state.update(o, now=T0 + timedelta(seconds=secs)))
    return found


LYING = obs(person_present=True, posture="lying", motion="still")


def test_lying_without_on_floor_is_not_a_fall():
    assert not _run(CareState(), (0, LYING), (60, LYING), (600, LYING)) & {"fall", "fall_motionless"}


def test_explicit_on_floor_still_alerts():
    down = {**LYING, "on_floor": True}
    assert "fall_motionless" in _run(CareState(), (0, down), (30, down))


def test_long_daytime_lying_gets_a_gentle_check():
    events = CareState().update(LYING, now=T0)
    assert events == []
    state = CareState()
    state.update(LYING, now=T0)
    late = state.update(LYING, now=T0 + timedelta(minutes=31))
    assert [(e.kind, e.level) for e in late] == [("long_lying", "MEDIUM")]


def test_sleeping_at_night_raises_nothing():
    night = T0.replace(hour=23, minute=30)
    state = CareState()
    state.update(LYING, now=night)
    assert state.update(LYING, now=night + timedelta(minutes=45)) == []


def test_a_brief_tracking_dropout_does_not_restart_the_lying_timer():
    state = CareState()
    state.update(LYING, now=T0)
    state.update(obs(), now=T0 + timedelta(seconds=60))
    state.update(LYING, now=T0 + timedelta(seconds=90))
    assert state.lying_since == T0


def test_getting_up_or_leaving_clears_the_lying_timer():
    state = CareState()
    state.update(LYING, now=T0)
    state.update(obs(person_present=True, posture="standing"), now=T0 + timedelta(minutes=1))
    assert state.lying_since is None
    state.update(LYING, now=T0 + timedelta(minutes=2))
    state.update(obs(), now=T0 + timedelta(minutes=10))
    assert state.lying_since is None
