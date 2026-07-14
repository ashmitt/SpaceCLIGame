import pytest
from src.scheduler.models import Task, TaskStatus
from src.scheduler.algorithms import (
    FIFOScheduler,
    PriorityScheduler,
    SJFScheduler,
    EDFScheduler
)

def test_fifo_scheduler():
    scheduler = FIFOScheduler()
    t1 = Task(id=1, name="Task 1", priority=3, duration=5, remaining_duration=5)
    t2 = Task(id=2, name="Task 2", priority=1, duration=10, remaining_duration=10)
    t3 = Task(id=3, name="Task 3", priority=5, duration=2, remaining_duration=2)

    sorted_tasks = scheduler.sort_tasks([t3, t1, t2])
    assert [t.id for t in sorted_tasks] == [1, 2, 3]

def test_priority_scheduler():
    scheduler = PriorityScheduler()
    t1 = Task(id=1, name="Task 1", priority=3, duration=5, remaining_duration=5)
    t2 = Task(id=2, name="Task 2", priority=1, duration=10, remaining_duration=10)
    t3 = Task(id=3, name="Task 3", priority=5, duration=2, remaining_duration=2)

    sorted_tasks = scheduler.sort_tasks([t3, t1, t2])
    assert [t.id for t in sorted_tasks] == [2, 1, 3]

def test_sjf_scheduler():
    scheduler = SJFScheduler()
    t1 = Task(id=1, name="Task 1", priority=3, duration=5, remaining_duration=5)
    t2 = Task(id=2, name="Task 2", priority=1, duration=10, remaining_duration=10)
    t3 = Task(id=3, name="Task 3", priority=5, duration=2, remaining_duration=2)

    sorted_tasks = scheduler.sort_tasks([t2, t1, t3])
    assert [t.id for t in sorted_tasks] == [3, 1, 2]

def test_edf_scheduler():
    scheduler = EDFScheduler()
    t1 = Task(id=1, name="Task 1", priority=3, duration=5, remaining_duration=5, deadline=50)
    t2 = Task(id=2, name="Task 2", priority=1, duration=10, remaining_duration=10, deadline=10)
    t3 = Task(id=3, name="Task 3", priority=5, duration=2, remaining_duration=2, deadline=None)

    sorted_tasks = scheduler.sort_tasks([t3, t1, t2])
    assert [t.id for t in sorted_tasks] == [2, 1, 3]
