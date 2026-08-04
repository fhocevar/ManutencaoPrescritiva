from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class FeedbackCommand:
    event_id: UUID | None
    analysis_id: UUID | None
    rating: int
    comment: str | None
    created_by: str | None = None


@dataclass(frozen=True)
class ChatCommand:
    question: str
    fault: str | None = None
    limit: int = 5
