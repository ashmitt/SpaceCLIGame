# 09_API (API Specification) - ColonyOS

This document specifies the internal code APIs for the modular components of ColonyOS. Developers extending the simulation should conform to these interfaces.

---

## 1. Scheduler API

* **Module**: `src.scheduler.core`
* **Class**: `Scheduler`

### Methods

#### `submit_task`
```python
def submit_task(self, task: Task) -> int:
    """
    Submits a new task to the scheduling queue.
    
    Args:
        task: A Task instance with pre-configured parameters.
        
    Returns:
        The database ID of the successfully submitted task.
        
    Raises:
        DependencyError: If specified task dependencies do not exist in the database.
        ValueError: If task parameters (priority, duration) violate bounds.
    """
```

#### `cancel_task`
```python
def cancel_task(self, task_id: int) -> bool:
    """
    Cancels a PENDING or READY task, removing it from active scheduling.
    
    Args:
        task_id: The ID of the task to terminate.
        
    Returns:
        True if the task was successfully cancelled, False if it was already running or completed.
        
    Raises:
        TaskNotFoundError: If the task ID does not exist in the database.
    """
```

#### `set_policy`
```python
def set_policy(self, algorithm_name: str) -> None:
    """
    Swaps the active scheduling algorithm on the fly.
    
    Args:
        algorithm_name: One of ['fifo', 'priority', 'sjf', 'deadline', 'round_robin'].
        
    Raises:
        InvalidAlgorithmError: If the scheduling policy name is not recognized.
    """
```

---

## 2. Worker Manager API

* **Module**: `src.worker.manager`
* **Class**: `WorkerManager`

### Methods

#### `register_worker`
```python
def register_worker(self, name: str) -> Worker:
    """
    Spawns a new worker agent and inserts their default record into the DB.
    
    Args:
        name: Name of the colonist.
        
    Returns:
        The newly created Worker instance.
    """
```

#### `inflict_injury`
```python
def inflict_injury(self, worker_id: int, health_loss: int) -> WorkerState:
    """
    Applies health damage to a worker. If health reaches 0, kills the worker.
    
    Args:
        worker_id: The ID of the worker.
        health_loss: Integer amount of health to deduct.
        
    Returns:
        The updated WorkerState.
    """
```

---

## 3. Building Manager API

* **Module**: `src.building.manager`
* **Class**: `BuildingManager`

### Methods

#### `create_building`
```python
def create_building(self, building_type: str, name: str) -> int:
    """
    Triggers construction logic for a new building. Checks resource availability.
    
    Args:
        building_type: One of the supported BuildingType values.
        name: Visual descriptor.
        
    Returns:
        Building ID of the constructed/placed building.
        
    Raises:
        InsufficientResourcesError: If colony resource stockpiles cannot cover cost.
    """
```

---

## 4. Event Bus API

* **Module**: `src.event.bus`
* **Class**: `EventBus`

### Methods

#### `subscribe`
```python
def subscribe(self, event_type: str, callback: Callable[[Event], None], priority: int = 3) -> None:
    """
    Registers a handler callback to be invoked when an event type is published.
    
    Args:
        event_type: String identifier (e.g. "incident.solar_flare").
        callback: Function receiving an Event payload.
        priority: Processing order. Lower values execute first.
    """
```

#### `publish`
```python
def publish(self, event: Event) -> None:
    """
    Publishes an event to the Event Bus, triggering subscriber handlers.
    
    Args:
        event: An Event instance.
    """
```

---

## 5. Python API Usage Code Example

The code snippet below demonstrates how a developer uses the ColonyOS API to programmatically inject a repair task and register a callback listener for task completion:

```python
from src.event.bus import EventBus
from src.event.models import Event
from src.scheduler.core import Scheduler
from src.scheduler.models import Task, TaskStatus

# Initialize objects
event_bus = EventBus()
scheduler = Scheduler()

# 1. Define a completion callback handler
def on_repair_complete(event: Event):
    task_id = event.payload.get("task_id")
    print(f"[SYSTEM] Log Alert: Repair task {task_id} completed successfully.")

# 2. Subscribe to task completion events with Priority 1
event_bus.subscribe("task.completed", on_repair_complete, priority=1)

# 3. Create a task model
emergency_repair = Task(
    name="Emergency Life Support Patch",
    priority=1,
    duration=5,
    remaining_duration=5,
    status=TaskStatus.PENDING,
    dependencies=[]
)

# 4. Submit task to the Scheduler
task_id = scheduler.submit_task(emergency_repair)
print(f"Task successfully registered in DB Queue with ID: {task_id}")
```
