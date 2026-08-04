from datetime import datetime, timezone
from uuid import uuid4

from app.domain.entities import SimilarEvent
from app.domain.services import FaultPolicy, FrequencyCalculator


def test_normal_states_are_not_problems():
    for state in ("normal", "baseline", "teste", "acelerando", "motor_desligado"):
        assert FaultPolicy.is_problem(state) is False


def test_fault_is_problem():
    assert FaultPolicy.is_problem("cocked_rotor_2") is True


def test_frequency_per_month():
    reference = datetime(2026, 6, 1, tzinfo=timezone.utc)
    events = [
        SimilarEvent(uuid4(), 1, datetime(2026, 5, 1, tzinfo=timezone.utc), "fault", 0.1),
        SimilarEvent(uuid4(), 2, datetime(2026, 4, 1, tzinfo=timezone.utc), "fault", 0.2),
    ]
    assert FrequencyCalculator.per_month(events, reference) > 0
