from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRY = "RETRY"
    DEAD = "DEAD"


@dataclass
class Task:
    id: Optional[int]
    name: str
    priority: int
    duration: int
    remaining_duration: int
    worker_id: Optional[int] = None
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    dependencies: str = ""  # Comma-separated list of IDs, e.g. "1,2"
    deadline: Optional[int] = None
    created_tick: int = 0
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def get_dependency_ids(self) -> List[int]:
        if not self.dependencies or self.dependencies.strip() == "":
            return []
        try:
            return [int(x.strip()) for x in self.dependencies.split(",") if x.strip()]
        except ValueError:
            return []

    def is_ready(self, completed_ids: List[int]) -> bool:
        deps = self.get_dependency_ids()
        return all(dep_id in completed_ids for dep_id in deps)

    @classmethod
    def from_row(cls, row) -> "Task":
        return cls(
            id=row["id"],
            name=row["name"],
            priority=row["priority"],
            duration=row["duration"],
            remaining_duration=row["remaining_duration"],
            worker_id=row["worker_id"],
            status=TaskStatus(row["status"]),
            retry_count=row["retry_count"],
            dependencies=row["dependencies"] or "",
            deadline=row["deadline"],
            created_tick=row["created_tick"] if "created_tick" in row.keys() else 0,
            created_at=row["created_at"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
        )
