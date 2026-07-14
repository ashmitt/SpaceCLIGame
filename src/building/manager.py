import logging
from typing import Any, Dict

from src.core.resources import ResourceManager
from src.database.connection import DBHelper
from src.event.bus import EventBus
from src.event.models import Event

logger = logging.getLogger("ColonyOS.BuildingManager")


class BuildingManager:
    def __init__(self, db: DBHelper, event_bus: EventBus):
        self.db = db
        self.event_bus = event_bus

    def register_starting_buildings(self) -> None:
        """Constructs the initial Central Command Hub if empty."""
        count = self.db.fetch_one("SELECT COUNT(*) as c FROM buildings")["c"]
        if count == 0:
            logger.info("Registering starting Central Command Hub...")
            self.db.execute("""
                INSERT INTO buildings (name, type, level, health, efficiency, active)
                VALUES ('Central Command Hub', 'COMMAND_HUB', 1, 100, 1.0, 1)
                """)

    def tick_buildings(self, resource_mgr: ResourceManager, config_meta: Dict[str, Any]) -> None:
        """Processes durability decay, power balances, and resource production."""
        # 1. Durability decay: decrease durability by 1% per tick for all buildings
        self.db.execute("UPDATE buildings SET health = MAX(0, health - 1) WHERE health > 0")

        # Recalculate efficiency (efficiency = health / 100.0)
        self.db.execute("UPDATE buildings SET efficiency = health / 100.0")

        # 2. Query all buildings
        buildings = self.db.fetch_all("SELECT * FROM buildings")

        total_production_power = 0.0
        total_consumption_power = 0.0

        active_consumers = []

        for b in buildings:
            b_id = b["id"]
            b_type = b["type"]
            b_active = b["active"]
            b_health = b["health"]
            efficiency = b["efficiency"]

            if b_health <= 0:
                continue

            meta = config_meta.get(b_type, {})
            power_impact = meta.get("power_impact", 0.0)

            if b_active:
                if power_impact > 0:
                    # Solar array generation scales with efficiency
                    total_production_power += power_impact * efficiency
                elif power_impact < 0:
                    # Consumption draws full capacity if active
                    total_consumption_power += abs(power_impact)
                    active_consumers.append((b_id, b_type, abs(power_impact)))

        # Power Grid Net Math
        net_power = total_production_power - total_consumption_power

        # Fetch current power stockpile
        res_dict = resource_mgr.get_resources()
        power_stock = res_dict.get("Power", {}).get("amount", 0.0)

        blackout = False
        if net_power >= 0:
            # Power surplus: add to battery grids
            resource_mgr.add_resource("Power", net_power)
        else:
            # Power deficit: try to drain batteries
            deficit = abs(net_power)
            success = resource_mgr.consume_resource("Power", deficit)
            if not success:
                blackout = True
                logger.warning(
                    "Power grid experienced a blackout! Shutting down non-essential systems..."
                )
                self.event_bus.publish(
                    Event(
                        event_type="incident.power_surge",
                        payload={"severity": "WARNING"},
                        publisher="BUILDING_MANAGER",
                    )
                )

        # 3. Handle Blackout / Brownout: shut down non-essential consumers
        if blackout:
            # Order of deactivation priority: HYDROPONICS_DOME (least critical), WATER_EXTRACTOR, LIFE_SUPPORT (most critical)
            deactivation_order = ["HYDROPONICS_DOME", "WATER_EXTRACTOR", "LIFE_SUPPORT"]

            # Deactivate consumers one by one until consumption matches production
            for type_to_deactivate in deactivation_order:
                for b_id, b_type, power_draw in active_consumers:
                    if b_type == type_to_deactivate:
                        # Deactivate in database
                        self.db.execute("UPDATE buildings SET active = 0 WHERE id = ?", (b_id,))
                        logger.warning(
                            f"Power brownout: Deactivated building {b_type} (ID: {b_id}) to balance grid."
                        )
                        total_consumption_power -= power_draw

                        net_power = total_production_power - total_consumption_power
                        if net_power >= 0:
                            break
                if net_power >= 0:
                    break

        # 4. Process Operational Production (Food, Water, Oxygen)
        # Fetch active buildings again to account for brownout deactivations
        active_buildings = self.db.fetch_all(
            "SELECT * FROM buildings WHERE active = 1 AND health > 0"
        )
        for b in active_buildings:
            b_type = b["type"]
            efficiency = b["efficiency"]

            meta = config_meta.get(b_type, {})
            prod_rate = meta.get("production_rate", {})

            # Produce resources
            for res_name, base_rate in prod_rate.items():
                actual_prod = base_rate * efficiency
                resource_mgr.add_resource(res_name, actual_prod)
