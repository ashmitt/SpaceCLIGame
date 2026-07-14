from abc import ABC, abstractmethod
from typing import List

from src.scheduler.models import Task


class BaseScheduler(ABC):
    @abstractmethod
    def sort_tasks(self, tasks: List[Task]) -> List[Task]:
        """Returns the sorted list of ready tasks according to scheduling policy."""
        pass


class FIFOScheduler(BaseScheduler):
    def sort_tasks(self, tasks: List[Task]) -> List[Task]:
        # FIFO is order of creation (Task ID serves as incrementing creation counter)
        return sorted(tasks, key=lambda t: t.id if t.id is not None else 999999)


class PriorityScheduler(BaseScheduler):
    def sort_tasks(self, tasks: List[Task]) -> List[Task]:
        # Sort by priority ascending (1 = highest, 5 = lowest), then by creation order (ID)
        return sorted(tasks, key=lambda t: (t.priority, t.id if t.id is not None else 999999))


class SJFScheduler(BaseScheduler):
    def sort_tasks(self, tasks: List[Task]) -> List[Task]:
        # Shortest Job First: sort by remaining duration, then priority, then ID
        return sorted(
            tasks,
            key=lambda t: (t.remaining_duration, t.priority, t.id if t.id is not None else 999999),
        )


class EDFScheduler(BaseScheduler):
    def sort_tasks(self, tasks: List[Task]) -> List[Task]:
        # Earliest Deadline First: sort by deadline. If deadline is None, place at the very end.
        return sorted(
            tasks,
            key=lambda t: (
                t.deadline if t.deadline is not None else 999999,
                t.priority,
                t.id if t.id is not None else 999999,
            ),
        )


class RoundRobinScheduler(BaseScheduler):
    def sort_tasks(self, tasks: List[Task]) -> List[Task]:
        # Round Robin in terms of queue selection functions like FIFO.
        # The execution slice limits are handled inside the worker execution loop.
        return sorted(tasks, key=lambda t: t.id if t.id is not None else 999999)
