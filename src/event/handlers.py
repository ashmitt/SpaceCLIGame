import json
import logging
import time

from src.database.connection import DBHelper
from src.event.bus import EventBus
from src.event.models import Event

logger = logging.getLogger("ColonyOS.EventHandlers")


class GameEventHandlers:
    def __init__(self, db: DBHelper, event_bus: EventBus):
        self.db = db
        self.event_bus = event_bus

    def register_all(self):
        # Universal log handler
        self.event_bus.subscribe("*", self.log_to_db, priority=5)
        # Incident damage handlers
        self.event_bus.subscribe("incident.meteor_strike", self.handle_meteor_strike, priority=2)
        self.event_bus.subscribe("incident.power_surge", self.handle_power_surge, priority=2)
        self.event_bus.subscribe("incident.solar_flare", self.handle_solar_flare, priority=2)
        # Task completion handlers
        self.event_bus.subscribe("task.completed", self.handle_task_completed, priority=1)
        # Resource depletion warnings
        self.event_bus.subscribe("resource.depleted", self.handle_resource_depletion, priority=3)

    def log_to_db(self, event: Event):
        """Universal subscriber to write all events to the syslog database table."""
        level = "INFO"
        if event.event_type.startswith("incident"):
            level = "WARNING" if event.payload.get("severity") != "CRITICAL" else "CRITICAL"
        elif event.event_type.endswith("depleted") or event.event_type.endswith("failed"):
            level = "ERROR"

        msg = f"Event [{event.event_type}] published. Payload: {json.dumps(event.payload)}"
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(event.timestamp))
        self.db.execute(
            "INSERT INTO logs (timestamp, level, message, module) VALUES (?, ?, ?, ?)",
            (timestamp, level, msg, event.publisher),
        )

    def handle_meteor_strike(self, event: Event):
        """Deducts durability from a target building and triggers a repair task."""
        building_id = event.payload.get("building_id")
        damage = event.payload.get("damage", 30)

        # Get building info
        row = self.db.fetch_one("SELECT * FROM buildings WHERE id = ?", (building_id,))
        if not row:
            return

        building_name = row["name"]
        new_health = max(0, row["health"] - damage)

        self.db.execute(
            "UPDATE buildings SET health = ?, efficiency = ? WHERE id = ?",
            (new_health, new_health / 100.0, building_id),
        )

        logger.warning(
            f"Meteor strike hit {building_name} (ID: {building_id}) for {damage} damage! Durability now: {new_health}%"
        )

        # Trigger repair task generation if health is below 100
        if new_health < 100:
            self._generate_repair_task(building_id, building_name)

    def handle_power_surge(self, event: Event):
        """Damages solar arrays or life support systems."""
        damage = event.payload.get("damage", 25)
        # Select random solar array or life support unit to damage
        row = self.db.fetch_one(
            "SELECT * FROM buildings WHERE type IN ('SOLAR_ARRAY', 'LIFE_SUPPORT') AND health > 0 ORDER BY RANDOM() LIMIT 1"
        )
        if row:
            building_id = row["id"]
            building_name = row["name"]
            new_health = max(0, row["health"] - damage)

            self.db.execute(
                "UPDATE buildings SET health = ?, efficiency = ? WHERE id = ?",
                (new_health, new_health / 100.0, building_id),
            )
            logger.warning(
                f"Power surge damaged {building_name} (ID: {building_id}) for {damage} damage! Durability now: {new_health}%"
            )

            if new_health < 100:
                self._generate_repair_task(building_id, building_name)

    def handle_solar_flare(self, event: Event):
        """Causes temporary grid instability, damages Solar Arrays, and drains power."""
        # Deduct some power from resources
        self.db.execute(
            "UPDATE resources SET amount = MAX(0.0, amount - 50.0) WHERE name = 'Power'"
        )
        logger.warning("Solar flare detected! Grid experienced power loss of 50.0 kW.")

        # Damage all active solar arrays by 10%
        self.db.execute(
            "UPDATE buildings SET health = MAX(0, health - 10), efficiency = MAX(0.0, (health - 10)/100.0) WHERE type = 'SOLAR_ARRAY'"
        )

    def handle_task_completed(self, event: Event):
        """Restores building health if a repair task completes."""
        task_name = event.payload.get("task_name", "")
        if task_name.startswith("Repair "):
            # Parse building id from task name or payload
            building_id = event.payload.get("building_id")
            if building_id:
                # Fully restore building health to 100%
                self.db.execute(
                    "UPDATE buildings SET health = 100, efficiency = 1.0 WHERE id = ?",
                    (building_id,),
                )
                row = self.db.fetch_one("SELECT name FROM buildings WHERE id = ?", (building_id,))
                b_name = row["name"] if row else f"Building #{building_id}"
                logger.info(
                    f"[HANDLER] Building {b_name} (ID: {building_id}) has been repaired to 100% durability."
                )

    def handle_resource_depletion(self, event: Event):
        resource_name = event.payload.get("resource_name")
        logger.error(f"[CRITICAL] Stockpile DEPLETED: {resource_name} is at 0.0!")

    def _generate_repair_task(self, building_id: int, building_name: str):
        task_name = f"Repair {building_name} (ID: {building_id})"

        # Check if identical repair task is already in queue
        existing = self.db.fetch_one(
            "SELECT id FROM tasks WHERE name = ? AND status IN ('PENDING', 'READY', 'RUNNING')",
            (task_name,),
        )
        if existing:
            return

        # Insert new high-priority repair task
        # Cost is 5 ticks
        self.db.execute(
            """
            INSERT INTO tasks (name, priority, duration, remaining_duration, status, dependencies)
            VALUES (?, ?, ?, ?, 'PENDING', '')
            """,
            (task_name, 1, 5, 5),  # priority 1 = high, duration = 5 ticks
        )
        logger.info(f"Auto-generated repair task: '{task_name}' submitted to queue.")
