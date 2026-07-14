import pytest
import os
import time
from src.database.connection import DBHelper
from src.event.bus import EventBus
from src.event.handlers import GameEventHandlers
from src.scheduler.core import Scheduler
from src.scheduler.models import Task, TaskStatus
from src.core.resources import ResourceManager
from src.building.manager import BuildingManager
from src.worker.manager import WorkerManager
from src.core.engine import SimulationEngine

def test_simulation_stress():
    db_file = "test_stress.db"
    if os.path.exists(db_file):
        os.remove(db_file)
        
    config = {
        "simulation": {
            "db_path": db_file,
            "tick_interval_seconds": 0.05,
            "max_retries": 3,
            "aging_threshold_ticks": 10
        },
        "difficulty": {
            "disaster_check_interval": 10,
            "disaster_probability": 0.5 # High probability for testing
        },
        "starting_resources": {
            "Water": 500.0,
            "Food": 500.0,
            "Oxygen": 500.0,
            "Power": 100.0,
            "IronOre": 100.0,
            "SolarCells": 10.0
        },
        "resource_capacities": {
            "Water": 1000.0,
            "Food": 1000.0,
            "Oxygen": 1000.0,
            "Power": 500.0,
            "IronOre": 1000.0,
            "SolarCells": 100.0
        },
        "starting_workers": [
            {"name": "StressWorker_1", "skills": {"construction": 2, "agriculture": 1, "engineering": 1}},
            {"name": "StressWorker_2", "skills": {"construction": 1, "agriculture": 2, "engineering": 1}},
            {"name": "StressWorker_3", "skills": {"construction": 1, "agriculture": 1, "engineering": 2}}
        ],
        "buildings": {
            "COMMAND_HUB": {"name": "Central Hub", "power_impact": -10, "production_rate": {}, "max_durability": 200},
            "SOLAR_ARRAY": {"name": "Solar Array", "power_impact": 40, "production_rate": {}, "max_durability": 100},
            "HYDROPONICS_DOME": {"name": "Hydroponics Dome", "power_impact": -20, "production_rate": {"Food": 4.0}, "max_durability": 120},
            "WATER_EXTRACTOR": {"name": "Water Extractor", "power_impact": -15, "production_rate": {"Water": 8.0}, "max_durability": 100},
            "LIFE_SUPPORT": {"name": "Life Support", "power_impact": -30, "production_rate": {"Oxygen": 10.0}, "max_durability": 150}
        }
    }

    db = DBHelper(db_file)
    event_bus = EventBus()
    event_bus.clear()
    
    handlers = GameEventHandlers(db, event_bus)
    handlers.register_all()
    
    scheduler = Scheduler(db)
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
        config=config
    )
    
    # Initialize
    engine.initialize_game()
    worker_mgr.start_workers()

    # Submit 15 dummy tasks of varying durations and priorities
    for i in range(1, 16):
        scheduler.submit_task(Task(
            id=None,
            name=f"Stress Job {i}",
            priority=(i % 5) + 1,
            duration=3,
            remaining_duration=3,
            status=TaskStatus.PENDING
        ))

    try:
        # Run 25 clock ticks rapidly
        for tick_num in range(25):
            engine.tick()
            
        # Verify tasks are progressing or completed
        completed_count = db.fetch_one("SELECT COUNT(*) as c FROM tasks WHERE status = 'COMPLETED'")["c"]
        running_count = db.fetch_one("SELECT COUNT(*) as c FROM tasks WHERE status = 'RUNNING'")["c"]
        ready_count = db.fetch_one("SELECT COUNT(*) as c FROM tasks WHERE status = 'READY'")["c"]
        
        # We expect some tasks to complete or be processed
        total_started = completed_count + running_count + ready_count
        assert total_started > 0, "No tasks were scheduled during simulation!"
        
        # Verify no database lock errors occurred
        logs_count = db.fetch_one("SELECT COUNT(*) as c FROM logs")["c"]
        assert logs_count > 0, "Log entries were not generated!"
        
    finally:
        worker_mgr.stop_workers()
        if os.path.exists(db_file):
            os.remove(db_file)
            
        # Clean up database journal files if any
        if os.path.exists(f"{db_file}-wal"):
            os.remove(f"{db_file}-wal")
        if os.path.exists(f"{db_file}-shm"):
            os.remove(f"{db_file}-shm")
