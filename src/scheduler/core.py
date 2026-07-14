import logging
from typing import Dict, Optional

from src.database.connection import DBHelper
from src.scheduler.algorithms import (
    BaseScheduler,
    EDFScheduler,
    FIFOScheduler,
    PriorityScheduler,
    RoundRobinScheduler,
    SJFScheduler,
)
from src.scheduler.models import Task, TaskStatus

logger = logging.getLogger("ColonyOS.Scheduler")


class Scheduler:
    def __init__(self, db: DBHelper):
        self.db = db
        self.active_policy = "priority"
        self.algorithms: Dict[str, BaseScheduler] = {
            "fifo": FIFOScheduler(),
            "priority": PriorityScheduler(),
            "sjf": SJFScheduler(),
            "deadline": EDFScheduler(),
            "round_robin": RoundRobinScheduler(),
        }

    def set_policy(self, policy_name: str) -> None:
        name = policy_name.lower().strip()
        if name not in self.algorithms:
            raise ValueError(f"Invalid scheduling algorithm: {policy_name}")
        self.active_policy = name
        logger.info(f"Scheduling policy changed to: '{self.active_policy.upper()}'")

        # Save active policy in game_state
        self.db.execute(
            "INSERT OR REPLACE INTO game_state (key, value) VALUES ('active_scheduler', ?)",
            (self.active_policy,),
        )

    def get_current_tick(self) -> int:
        row = self.db.fetch_one("SELECT value FROM game_state WHERE key = 'current_tick'")
        return int(row["value"]) if row else 0

    def submit_task(self, task: Task) -> int:
        """Inserts a task into the database queue."""
        curr_tick = self.get_current_tick()
        task.created_tick = curr_tick

        # If dependencies are empty, set to READY, otherwise PENDING
        status = TaskStatus.READY.value if not task.dependencies else TaskStatus.PENDING.value

        rowid = self.db.execute(
            """
            INSERT INTO tasks (name, priority, duration, remaining_duration, worker_id, status, retry_count, dependencies, deadline, created_tick)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task.name,
                task.priority,
                task.duration,
                task.duration,
                task.worker_id,
                status,
                task.retry_count,
                task.dependencies,
                task.deadline,
                task.created_tick,
            ),
        )
        logger.info(f"Task '{task.name}' (ID: {rowid}) submitted with priority {task.priority}")
        return rowid

    def cancel_task(self, task_id: int) -> bool:
        """Cancels a task if it is not already running or completed."""
        row = self.db.fetch_one("SELECT status FROM tasks WHERE id = ?", (task_id,))
        if not row:
            return False

        status = row["status"]
        if status in (TaskStatus.RUNNING.value, TaskStatus.COMPLETED.value, TaskStatus.DEAD.value):
            return False

        self.db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        logger.info(f"Task ID {task_id} successfully cancelled.")
        return True

    def resolve_dependencies(self) -> None:
        """Transitions PENDING tasks to READY if their dependencies are met."""
        # Get all completed tasks
        completed_rows = self.db.fetch_all("SELECT id FROM tasks WHERE status = 'COMPLETED'")
        completed_ids = {row["id"] for row in completed_rows}

        # Get all pending tasks
        pending_rows = self.db.fetch_all("SELECT * FROM tasks WHERE status = 'PENDING'")
        for row in pending_rows:
            task = Task.from_row(row)
            if task.is_ready(completed_ids):
                self.db.execute(
                    "UPDATE tasks SET status = ? WHERE id = ?", (TaskStatus.READY.value, task.id)
                )
                logger.debug(
                    f"Task ID {task.id} ('{task.name}') dependencies resolved. Status -> READY."
                )

    def get_next_ready_task(self) -> Optional[Task]:
        """Resolves dependencies, fetches, sorts, and returns the next task to run."""
        self.resolve_dependencies()

        # Fetch all READY tasks
        ready_rows = self.db.fetch_all("SELECT * FROM tasks WHERE status = 'READY'")
        if not ready_rows:
            return None

        tasks = [Task.from_row(row) for row in ready_rows]

        # Sort tasks according to active policy
        sorted_tasks = self.algorithms[self.active_policy].sort_tasks(tasks)
        return sorted_tasks[0] if sorted_tasks else None

    def apply_aging(self, threshold_ticks: int = 20) -> None:
        """Increases priority of tasks waiting in queue for a long time to prevent starvation."""
        curr_tick = self.get_current_tick()

        # Select all ready or pending tasks
        rows = self.db.fetch_all("SELECT * FROM tasks WHERE status IN ('READY', 'PENDING')")
        for row in rows:
            task = Task.from_row(row)
            wait_ticks = curr_tick - task.created_tick
            if wait_ticks >= threshold_ticks:
                # If priority > 1, we can increase it by decrementing the value
                if task.priority > 1:
                    new_priority = task.priority - 1
                    self.db.execute(
                        "UPDATE tasks SET priority = ? WHERE id = ?", (new_priority, task.id)
                    )
                    # Log warning
                    msg = f"Task '{task.name}' (ID: {task.id}) waiting for {wait_ticks} ticks. Aging priority from {task.priority} to {new_priority}."
                    logger.warning(msg)

                    # Write to system logs table
                    self.db.execute(
                        "INSERT INTO logs (level, message, module) VALUES ('WARNING', ?, 'SCHEDULER')",
                        (msg,),
                    )
