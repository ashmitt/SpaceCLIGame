import logging
from typing import Dict, List

from src.database.connection import DBHelper
from src.event.bus import EventBus
from src.worker.thread import WorkerThread

logger = logging.getLogger("ColonyOS.WorkerManager")


class WorkerManager:
    def __init__(self, db: DBHelper, event_bus: EventBus):
        self.db = db
        self.event_bus = event_bus
        self.threads: Dict[int, WorkerThread] = {}

    def register_starting_workers(self, starting_workers: List[dict]) -> None:
        """Populates the database with initial workers if empty."""
        count = self.db.fetch_one("SELECT COUNT(*) as c FROM workers")["c"]
        if count == 0:
            logger.info("Registering starting workers from config...")
            for w in starting_workers:
                skills = w.get("skills", {})
                self.db.execute(
                    """
                    INSERT INTO workers (name, health, energy, experience, skill_construction, skill_agriculture, skill_engineering, state)
                    VALUES (?, 100, 100, 0, ?, ?, ?, 'IDLE')
                    """,
                    (
                        w["name"],
                        skills.get("construction", 1),
                        skills.get("agriculture", 1),
                        skills.get("engineering", 1),
                    ),
                )

    def start_workers(self) -> None:
        """Spawns and starts a worker thread for each active worker in the database."""
        self.stop_workers()  # Clean up any existing threads

        workers = self.db.fetch_all("SELECT id FROM workers WHERE state != 'DEAD'")
        for w in workers:
            w_id = w["id"]
            thread = WorkerThread(w_id, self.db, self.event_bus)
            self.threads[w_id] = thread
            thread.start()
        logger.info(f"Spawned {len(self.threads)} worker execution threads.")

    def tick_workers(self) -> None:
        """Signals all worker threads to execute one step and blocks until all complete."""
        # Clean up any threads for workers that died
        dead_ids = []
        for w_id, thread in list(self.threads.items()):
            if not thread.is_alive():
                dead_ids.append(w_id)
        for w_id in dead_ids:
            del self.threads[w_id]

        # Trigger threads
        for thread in self.threads.values():
            thread.done_event.clear()
            thread.tick_event.set()

        # Wait for all threads to set their done_event
        for w_id, thread in self.threads.items():
            success = thread.done_event.wait(timeout=2.0)
            if not success:
                logger.warning(f"Worker thread {w_id} did not complete tick work within timeout.")

    def stop_workers(self) -> None:
        """Gracefully halts and terminates all worker threads."""
        if not self.threads:
            return

        logger.info("Stopping all worker threads...")
        for thread in self.threads.values():
            thread.stop()

        for thread in self.threads.values():
            thread.join(timeout=1.0)

        self.threads.clear()
        logger.info("All worker threads joined and cleared.")
