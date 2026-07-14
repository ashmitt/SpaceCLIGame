import logging
import os
import sys
from pathlib import Path

# Ensure the project root is on sys.path when this file is run directly
# (e.g. `python src/main.py` or `python main.py` from inside src/).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import yaml

from src.building.manager import BuildingManager
from src.cli.shell import ColonyShell
from src.core.engine import SimulationEngine
from src.core.resources import ResourceManager
from src.database.connection import DBHelper
from src.event.bus import EventBus
from src.event.handlers import GameEventHandlers
from src.scheduler.core import Scheduler
from src.worker.manager import WorkerManager

logger = logging.getLogger("ColonyOS.Main")


def _setup_logging() -> None:
    log_path = _PROJECT_ROOT / "colony_os.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
        ],
        force=True,
    )


def main():
    os.chdir(_PROJECT_ROOT)
    _setup_logging()

    # Load config from project root regardless of launch directory
    config_path = _PROJECT_ROOT / "config.yaml"
    if config_path.exists():
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
    else:
        config = {}
        logger.warning(f"Config file '{config_path}' not found, using empty defaults.")

    db_path = config.get("simulation", {}).get("db_path", "colony.db")
    if not os.path.isabs(db_path):
        db_path = str(_PROJECT_ROOT / db_path)

    logger.info("Initializing ColonyOS subsystems...")

    db = DBHelper(db_path)
    event_bus = EventBus()

    event_bus.clear()
    handlers = GameEventHandlers(db, event_bus)
    handlers.register_all()

    scheduler = Scheduler(db)

    cached_policy = db.fetch_one("SELECT value FROM game_state WHERE key = 'active_scheduler'")
    if cached_policy:
        scheduler.active_policy = cached_policy["value"]

    resource_mgr = ResourceManager(db, event_bus)
    building_mgr = BuildingManager(db, event_bus)
    worker_mgr = WorkerManager(db, event_bus)

    engine = SimulationEngine(
        db=db,
        event_bus=event_bus,
        scheduler=scheduler,
        resource_mgr=resource_mgr,
        building_mgr=building_mgr,
        worker_mgr=worker_mgr,
        config=config,
    )

    engine.initialize_game()
    worker_mgr.start_workers()

    shell = ColonyShell(engine)
    try:
        shell.cmdloop()
    except KeyboardInterrupt:
        print("\n[SYSTEM] Received interrupt signal. Shutting down...")
    finally:
        engine.stop_daemon()


if __name__ == "__main__":
    main()
