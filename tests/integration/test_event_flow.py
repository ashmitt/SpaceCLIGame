import pytest
import os
from src.database.connection import DBHelper
from src.event.bus import EventBus
from src.event.models import Event
from src.event.handlers import GameEventHandlers

def test_event_bus_pub_sub():
    eb = EventBus()
    eb.clear()
    
    received = []
    def callback(event):
        received.append(event)
        
    eb.subscribe("test.event", callback, priority=1)
    
    ev = Event(event_type="test.event", payload={"key": "val"})
    eb.publish(ev)
    
    assert len(received) == 1
    assert received[0].payload["key"] == "val"

def test_meteor_strike_flow():
    db_file = "test_event_flow.db"
    if os.path.exists(db_file):
        os.remove(db_file)
        
    db = DBHelper(db_file)
    eb = EventBus()
    eb.clear()
    
    # Register handlers
    handlers = GameEventHandlers(db, eb)
    handlers.register_all()
    
    # Insert a dummy solar array building
    b_id = db.execute(
        "INSERT INTO buildings (name, type, level, health, efficiency, active) VALUES ('Solar Test', 'SOLAR_ARRAY', 1, 100, 1.0, 1)"
    )
    
    # Publish meteor strike on the building
    eb.publish(Event(
        event_type="incident.meteor_strike",
        payload={"building_id": b_id, "damage": 40},
        publisher="TEST_SUITE"
    ))
    
    # Verify building health decreased by 40
    row = db.fetch_one("SELECT health, efficiency FROM buildings WHERE id = ?", (b_id,))
    assert row["health"] == 60
    assert row["efficiency"] == 0.6
    
    # Verify repair task auto-created in tasks table
    task = db.fetch_one("SELECT * FROM tasks WHERE name LIKE ?", (f"%Repair Solar Test (ID: {b_id})%",))
    assert task is not None
    assert task["status"] == "PENDING"
    assert task["priority"] == 1
    
    # Clean up
    if os.path.exists(db_file):
        os.remove(db_file)
