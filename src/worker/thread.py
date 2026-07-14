import logging
import threading

from src.database.connection import DBHelper
from src.event.bus import EventBus
from src.event.models import Event
from src.scheduler.models import TaskStatus

logger = logging.getLogger("ColonyOS.WorkerThread")


class WorkerThread(threading.Thread):
    def __init__(self, worker_id: int, db: DBHelper, event_bus: EventBus):
        super().__init__(name=f"WorkerThread_{worker_id}")
        self.worker_id = worker_id
        self.db = db
        self.event_bus = event_bus

        # Synchronization Events
        self.tick_event = threading.Event()
        self.done_event = threading.Event()
        self.stop_event = threading.Event()

        # Round Robin Tracking
        self.quantum_ticks_spent = 0

    def stop(self) -> None:
        self.stop_event.set()
        self.tick_event.set()  # Wake up to exit

    def run(self) -> None:
        logger.info(f"Worker Thread {self.worker_id} started.")
        while not self.stop_event.is_set():
            # Wait for the next tick signal
            self.tick_event.wait()
            if self.stop_event.is_set():
                break

            try:
                self._perform_tick_work()
            except Exception as e:
                logger.error(f"Error in worker thread {self.worker_id}: {e}", exc_info=True)
            finally:
                # Signal that this worker is done with the tick
                self.tick_event.clear()
                self.done_event.set()

        logger.info(f"Worker Thread {self.worker_id} stopped.")

    def _perform_tick_work(self) -> None:
        # Fetch current state from DB
        row = self.db.fetch_one("SELECT * FROM workers WHERE id = ?", (self.worker_id,))
        if not row:
            return

        state = row["state"]
        health = row["health"]
        energy = row["energy"]
        current_task_id = row["current_task_id"]

        if state == "DEAD":
            self.stop()
            return

        # Check Active Scheduler Algorithm
        policy_row = self.db.fetch_one(
            "SELECT value FROM game_state WHERE key = 'active_scheduler'"
        )
        active_policy = policy_row["value"] if policy_row else "priority"

        if state == "WORKING" and current_task_id:
            # Fetch task
            task_row = self.db.fetch_one("SELECT * FROM tasks WHERE id = ?", (current_task_id,))
            if not task_row:
                # Task missing, reset worker
                self._reset_worker_state()
                return

            task_name = task_row["name"]
            remaining_dur = task_row["remaining_duration"]
            task_status = task_row["status"]

            # Update status to RUNNING if it was READY
            if task_status == TaskStatus.READY.value:
                self.db.execute(
                    "UPDATE tasks SET status = ?, started_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (TaskStatus.RUNNING.value, current_task_id),
                )
                self.quantum_ticks_spent = 0

            # Round Robin time-slice check
            if (
                active_policy == "round_robin"
                and self.quantum_ticks_spent >= 3
                and remaining_dur > 0
            ):
                # Quantum limit hit, context switch
                msg = f"Round Robin quantum expired. Task '{task_name}' (ID: {current_task_id}) re-queued. Worker {row['name']} context-switched."
                logger.info(msg)

                # Re-queue task
                self.db.execute(
                    "UPDATE tasks SET status = ?, worker_id = NULL WHERE id = ?",
                    (TaskStatus.READY.value, current_task_id),
                )
                # Set worker idle
                self.db.execute(
                    "UPDATE workers SET state = 'IDLE', current_task_id = NULL WHERE id = ?",
                    (self.worker_id,),
                )
                self.quantum_ticks_spent = 0
                return

            # Perform 1 tick of work
            remaining_dur -= 1
            energy = max(0, energy - 3)  # consume 3 energy per work tick
            self.quantum_ticks_spent += 1

            if remaining_dur <= 0:
                # Task completed!
                self.db.execute(
                    "UPDATE tasks SET status = ?, remaining_duration = 0, completed_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (TaskStatus.COMPLETED.value, current_task_id),
                )
                self.db.execute(
                    "UPDATE workers SET state = 'IDLE', current_task_id = NULL, energy = ?, experience = experience + 10 WHERE id = ?",
                    (energy, self.worker_id),
                )

                # Parse building ID if task is a repair task
                building_id = None
                if task_name.startswith("Repair"):
                    # Extract building ID from name "Repair BuildingName (ID: X)"
                    try:
                        parts = task_name.split("(ID: ")
                        if len(parts) > 1:
                            building_id = int(parts[1].replace(")", "").strip())
                    except Exception:
                        pass

                # Publish completed event
                self.event_bus.publish(
                    Event(
                        event_type="task.completed",
                        payload={
                            "task_id": current_task_id,
                            "task_name": task_name,
                            "building_id": building_id,
                            "worker_id": self.worker_id,
                        },
                        publisher=f"WorkerThread_{self.worker_id}",
                    )
                )
            elif energy <= 0:
                # Worker is fatigued, drop task
                msg = f"Worker {row['name']} is FATIGUED! Task '{task_name}' (ID: {current_task_id}) dropped back to queue."
                logger.warning(msg)

                # Re-queue task
                self.db.execute(
                    "UPDATE tasks SET status = ?, worker_id = NULL WHERE id = ?",
                    (TaskStatus.READY.value, current_task_id),
                )
                # Set worker fatigued
                self.db.execute(
                    "UPDATE workers SET state = 'FATIGUED', current_task_id = NULL, energy = 0 WHERE id = ?",
                    (self.worker_id,),
                )
                self.quantum_ticks_spent = 0
            else:
                # Normal work update
                self.db.execute(
                    "UPDATE tasks SET remaining_duration = ? WHERE id = ?",
                    (remaining_dur, current_task_id),
                )
                self.db.execute(
                    "UPDATE workers SET energy = ? WHERE id = ?", (energy, self.worker_id)
                )

        elif state == "IDLE":
            # If idle, check if a task has been assigned in the DB (by Scheduler)
            if current_task_id:
                self.db.execute(
                    "UPDATE workers SET state = 'WORKING' WHERE id = ?", (self.worker_id,)
                )
                self.quantum_ticks_spent = 0

        elif state in ("FATIGUED", "RESTING"):
            # Recover energy
            energy = min(100, energy + 15)
            if energy >= 100:
                self.db.execute(
                    "UPDATE workers SET state = 'IDLE', energy = 100 WHERE id = ?",
                    (self.worker_id,),
                )
                logger.info(f"Worker {row['name']} energy restored. State -> IDLE.")
            else:
                self.db.execute(
                    "UPDATE workers SET state = 'RESTING', energy = ? WHERE id = ?",
                    (energy, self.worker_id),
                )

    def _reset_worker_state(self) -> None:
        self.db.execute(
            "UPDATE workers SET state = 'IDLE', current_task_id = NULL WHERE id = ?",
            (self.worker_id,),
        )
        self.quantum_ticks_spent = 0
