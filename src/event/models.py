import time
import uuid
from dataclasses import dataclass, field


@dataclass
class Event:
    event_type: str
    payload: dict = field(default_factory=dict)
    priority: int = 3
    publisher: str = "SYSTEM"
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
