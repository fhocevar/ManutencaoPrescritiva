from datetime import datetime

from app.domain.constants import NORMAL_STATES
from app.domain.entities import SimilarEvent


class FaultPolicy:
    @staticmethod
    def is_problem(fault: str) -> bool:
        return fault.strip().lower() not in NORMAL_STATES


class FrequencyCalculator:
    @staticmethod
    def per_month(events: list[SimilarEvent], reference: datetime) -> float:
        if not events:
            return 0.0
        oldest = min(event.created_at for event in events)
        months = max((reference - oldest).days / 30.4375, 1.0)
        return round(len(events) / months, 3)
