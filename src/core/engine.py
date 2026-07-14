import logging
import random
import threading
import time
from typing import Any, Dict, Optional

from src.building.manager import BuildingManager
from src.core.resources import ResourceManager
from src.database.connection import DBHelper
from src.event.bus import EventBus
from src.event.models import Event
from src.scheduler.core import Scheduler
from src.worker.manager import WorkerManager

logger = logging.getLogger("ColonyOS.SimulationEngine")


class SimulationEngine:
    def __init__(
        self,
        db: DBHelper,
        event_bus: EventBus,
        scheduler: Scheduler,
        resource_mgr: ResourceManager,
        building_mgr: BuildingManager,
        worker_mgr: WorkerManager,
        config: Dict[str, Any],
    ):
        self.db = db
        self.event_bus = event_bus
        self.scheduler = scheduler
        self.resource_mgr = resource_mgr
        self.building_mgr = building_mgr
        self.worker_mgr = worker_mgr
        self.config = config

        self.tick_interval = config.get("simulation", {}).get("tick_interval_seconds", 1.0)
        self.is_running_daemon = False
        self.daemon_thread: Optional[threading.Thread] = None

    def initialize_game(self) -> None:
        """Sets up default database values, resources, buildings, and workers."""
        self.db.init_db()

        # Seed resources
        start_res = self.config.get("starting_resources", {})
        capacities = self.config.get("resource_capacities", {})
        self.resource_mgr.register_starting_resources(start_res, capacities)

        # Seed workers
        start_workers = self.config.get("starting_workers", [])
        self.worker_mgr.register_starting_workers(start_workers)

        # Seed buildings
        self.building_mgr.register_starting_buildings()

        # Set current tick to 1 if not exists
        tick_row = self.db.fetch_one("SELECT value FROM game_state WHERE key = 'current_tick'")
        if not tick_row:
            self.db.execute("INSERT INTO game_state (key, value) VALUES ('current_tick', '1')")
            self.db.execute(
                "INSERT INTO game_state (key, value) VALUES ('active_scheduler', 'priority')"
            )
            self.db.execute("INSERT INTO game_state (key, value) VALUES ('game_over', 'RUNNING')")
            logger.info("New game state initialized successfully.")

    def get_current_tick(self) -> int:
        row = self.db.fetch_one("SELECT value FROM game_state WHERE key = 'current_tick'")
        return int(row["value"]) if row else 1

    def get_game_over_status(self) -> str:
        row = self.db.fetch_one("SELECT value FROM game_state WHERE key = 'game_over'")
        return row["value"] if row else "RUNNING"

    def tick(self) -> None:
        """Executes a single step forward in the simulation clock."""
        game_over = self.get_game_over_status()
        if game_over != "RUNNING":
            return

        current_tick = self.get_current_tick()
        next_tick = current_tick + 1

        # 1. Update tick counter in DB
        self.db.execute(
            "UPDATE game_state SET value = ? WHERE key = 'current_tick'", (str(next_tick),)
        )

        # 2. Worker Resource Consumption
        deprivations = self.resource_mgr.tick_worker_consumption()

        # Apply health penalties for resource deprivations
        workers = self.db.fetch_all("SELECT * FROM workers WHERE state != 'DEAD'")
        for w in workers:
            w_id = w["id"]
            w_name = w["name"]
            w_health = w["health"]

            damage = 0
            reasons = []
            if deprivations.get("Oxygen"):
                damage += 20
                reasons.append("Asphyxiation")
            if deprivations.get("Water"):
                damage += 5
                reasons.append("Dehydration")
            if deprivations.get("Food"):
                damage += 5
                reasons.append("Starvation")

            if damage > 0:
                new_health = max(0, w_health - damage)
                new_state = "DEAD" if new_health <= 0 else w["state"]

                self.db.execute(
                    "UPDATE workers SET health = ?, state = ? WHERE id = ?",
                    (new_health, new_state, w_id),
                )

                msg = f"Worker {w_name} suffered {damage} damage due to {', '.join(reasons)}. Health is now {new_health}%."
                self.db.execute(
                    "INSERT INTO logs (level, message, module) VALUES ('ERROR', ?, 'RESOURCE_MANAGER')",
                    (msg,),
                )
                logger.warning(msg)

                if new_state == "DEAD":
                    msg_dead = f"Worker {w_name} has died."
                    logger.error(msg_dead)
                    self.db.execute(
                        "INSERT INTO logs (level, message, module) VALUES ('CRITICAL', ?, 'WORKER_MANAGER')",
                        (msg_dead,),
                    )

        # 3. Building operational ticks & power grid balances
        b_meta = self.config.get("buildings", {})
        self.building_mgr.tick_buildings(self.resource_mgr, b_meta)

        # 4. Apply Starvation Aging
        aging_threshold = self.config.get("simulation", {}).get("aging_threshold_ticks", 20)
        self.scheduler.apply_aging(aging_threshold)

        # 5. Incident Dispatcher
        self._check_and_trigger_disaster(next_tick)

        # 6. Task Assignment Loop
        self._assign_ready_tasks_to_idle_workers()

        # 7. Step Worker Threads
        self.worker_mgr.tick_workers()

        # 8. Check End-Game Conditions
        self._check_end_game_conditions()

    def _check_and_trigger_disaster(self, tick: int) -> None:
        interval = self.config.get("difficulty", {}).get("disaster_check_interval", 15)
        prob = self.config.get("difficulty", {}).get("disaster_probability", 0.15)

        if tick % interval == 0:
            if random.random() < prob:
                # Select random incident
                incident_types = [
                    ("incident.meteor_strike", "METEOR_STRIKE"),
                    ("incident.power_surge", "POWER_SURGE"),
                    ("incident.solar_flare", "SOLAR_FLARE"),
                ]
                inc_type, name = random.choice(incident_types)

                payload = {"severity": "WARNING"}
                if inc_type == "incident.meteor_strike":
                    # Choose a building to damage
                    b = self.db.fetch_one(
                        "SELECT id FROM buildings WHERE health > 0 ORDER BY RANDOM() LIMIT 1"
                    )
                    if b:
                        payload["building_id"] = b["id"]
                        payload["damage"] = random.randint(20, 45)
                elif inc_type == "incident.power_surge":
                    payload["damage"] = random.randint(15, 30)

                # Broadcast
                self.event_bus.publish(
                    Event(event_type=inc_type, payload=payload, publisher="SIMULATION_ENGINE")
                )

    def _assign_ready_tasks_to_idle_workers(self) -> None:
        """Selects idle workers and assigns them ready tasks sequentially."""
        # Find idle workers
        idle_workers = self.db.fetch_all(
            "SELECT * FROM workers WHERE state = 'IDLE' AND current_task_id IS NULL"
        )
        for w in idle_workers:
            w_id = w["id"]
            w_name = w["name"]

            # Retrieve the next ready task from the queue
            task = self.scheduler.get_next_ready_task()
            if task:
                # Atomic assignment
                self.db.execute(
                    "UPDATE tasks SET worker_id = ?, status = 'READY' WHERE id = ?", (w_id, task.id)
                )
                self.db.execute(
                    "UPDATE workers SET current_task_id = ?, state = 'WORKING' WHERE id = ?",
                    (task.id, w_id),
                )
                logger.info(
                    f"Assigned task '{task.name}' (ID: {task.id}) to worker {w_name} (ID: {w_id})"
                )

    def _check_end_game_conditions(self) -> None:
        # Check depopulation
        living = self.db.fetch_one("SELECT COUNT(*) as c FROM workers WHERE health > 0")["c"]
        if living == 0:
            self.db.execute("UPDATE game_state SET value = 'FAILED' WHERE key = 'game_over'")
            msg = "ALL WORKERS DECEASED. COLONY OFFLINE. GAME OVER."
            logger.critical(msg)
            self.db.execute(
                "INSERT INTO logs (level, message, module) VALUES ('CRITICAL', ?, 'ENGINE')", (msg,)
            )
            return

        # Check Command Hub integrity
        hub = self.db.fetch_one("SELECT health FROM buildings WHERE type = 'COMMAND_HUB'")
        if hub and hub["health"] <= 0:
            self.db.execute("UPDATE game_state SET value = 'FAILED' WHERE key = 'game_over'")
            msg = "COMMAND HUB STRUCTURAL COLLAPSE. COLONY OFFLINE. GAME OVER."
            logger.critical(msg)
            self.db.execute(
                "INSERT INTO logs (level, message, module) VALUES ('CRITICAL', ?, 'ENGINE')", (msg,)
            )
            return

        # Check Victory: If a building named "Atmosphere Stabilizer" exists and is active at 100% health
        stabilizer = self.db.fetch_one(
            "SELECT health FROM buildings WHERE type = 'LIFE_SUPPORT' AND level >= 3"
        )
        # Let's say if we unlock a specific research or reach tick 500
        # For simplicity, if player researches and unlocks a "VICTORY" key or reaches 1000 ticks.
        # Let's define victory when they build a Life Support Level 3 and reach tick 200.
        curr_tick = self.get_current_tick()
        if stabilizer and stabilizer["health"] >= 95 and curr_tick >= 300:
            self.db.execute("UPDATE game_state SET value = 'VICTORY' WHERE key = 'game_over'")
            msg = "TERRAFORMING STABILIZED. COLONY NOMINAL. VICTORY ACHIEVED!"
            logger.info(msg)
            self.db.execute(
                "INSERT INTO logs (level, message, module) VALUES ('INFO', ?, 'ENGINE')", (msg,)
            )

    def start_daemon(self) -> None:
        """Starts background clock ticking daemon thread."""
        if self.is_running_daemon:
            return

        self.is_running_daemon = True
        self.worker_mgr.start_workers()  # Initialize threads

        self.daemon_thread = threading.Thread(
            target=self._daemon_loop, name="SimulationClockDaemon", daemon=True
        )
        self.daemon_thread.start()
        logger.info("Simulation clock daemon started.")

    def stop_daemon(self) -> None:
        """Stops the daemon ticking loop."""
        self.is_running_daemon = False
        if self.daemon_thread:
            self.daemon_thread.join(timeout=1.0)
            self.daemon_thread = None
        self.worker_mgr.stop_workers()
        logger.info("Simulation clock daemon stopped.")

    def _daemon_loop(self) -> None:
        while self.is_running_daemon:
            game_over = self.get_game_over_status()
            if game_over != "RUNNING":
                self.is_running_daemon = False
                break

            self.tick()
            time.sleep(self.tick_interval)
