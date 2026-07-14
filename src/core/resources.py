import logging
from typing import Dict

from src.database.connection import DBHelper
from src.event.bus import EventBus
from src.event.models import Event

logger = logging.getLogger("ColonyOS.ResourceManager")


class ResourceManager:
    def __init__(self, db: DBHelper, event_bus: EventBus):
        self.db = db
        self.event_bus = event_bus

    def register_starting_resources(
        self, starting_res: Dict[str, float], capacities: Dict[str, float]
    ) -> None:
        """Seeds the database with initial resources if empty."""
        count = self.db.fetch_one("SELECT COUNT(*) as c FROM resources")["c"]
        if count == 0:
            logger.info("Registering starting resources in database...")
            for name, amount in starting_res.items():
                cap = capacities.get(name, 100.0)
                self.db.execute(
                    "INSERT INTO resources (name, amount, capacity) VALUES (?, ?, ?)",
                    (name, amount, cap),
                )

    def get_resources(self) -> Dict[str, Dict[str, float]]:
        rows = self.db.fetch_all("SELECT * FROM resources")
        return {row["name"]: {"amount": row["amount"], "capacity": row["capacity"]} for row in rows}

    def add_resource(self, name: str, amount: float) -> bool:
        """Adds resources up to capacity."""
        row = self.db.fetch_one("SELECT amount, capacity FROM resources WHERE name = ?", (name,))
        if not row:
            return False

        new_amount = min(row["capacity"], row["amount"] + amount)
        self.db.execute("UPDATE resources SET amount = ? WHERE name = ?", (new_amount, name))
        return True

    def consume_resource(self, name: str, amount: float) -> bool:
        """Consumes resource and caps at 0.0. Returns False if depletion occurs."""
        row = self.db.fetch_one("SELECT amount FROM resources WHERE name = ?", (name,))
        if not row:
            return False

        available = row["amount"]
        depleted = False

        if available - amount <= 0.0:
            new_amount = 0.0
            depleted = True
        else:
            new_amount = available - amount

        self.db.execute("UPDATE resources SET amount = ? WHERE name = ?", (new_amount, name))

        if depleted:
            self.event_bus.publish(
                Event(
                    event_type="resource.depleted",
                    payload={"resource_name": name},
                    publisher="RESOURCE_MANAGER",
                )
            )
            return False
        return True

    def tick_worker_consumption(self) -> Dict[str, bool]:
        """
        Consumes survival resources for all workers.
        Returns a dict indicating if any resource is depleted (e.g. {'Food': True, 'Water': False, 'Oxygen': False}).
        """
        workers = self.db.fetch_all("SELECT state FROM workers WHERE state != 'DEAD'")

        food_needed = 0.0
        water_needed = 0.0
        oxygen_needed = 0.0

        for w in workers:
            state = w["state"]
            if state == "WORKING":
                food_needed += 1.0
                water_needed += 2.0
                oxygen_needed += 3.0
            else:  # IDLE, RESTING, FATIGUED, INJURED
                food_needed += 0.5
                water_needed += 1.0
                oxygen_needed += 3.0

        # Attempt to consume resources
        food_ok = self.consume_resource("Food", food_needed)
        water_ok = self.consume_resource("Water", water_needed)
        oxygen_ok = self.consume_resource("Oxygen", oxygen_needed)

        # Log consumption
        logger.debug(
            f"Resource Consumption - Food: {food_needed}kg, Water: {water_needed}L, Oxygen: {oxygen_needed}m3"
        )

        return {"Food": not food_ok, "Water": not water_ok, "Oxygen": not oxygen_ok}
