# 08_EVENT_SYSTEM - ColonyOS

## 1. Event Bus Architecture

ColonyOS utilizes a decoupled **Publish/Subscribe (Pub/Sub) Event Bus** pattern to propagate occurrences (disasters, alerts, completed tasks, building brownouts) to their respective handlers. This ensures core game physics and logical systems remain clean and independent.

```mermaid
graph LR
    subgraph Publishers
        WT[Worker Thread]
        ENG[Simulation Engine]
        CLI[User CLI]
    end

    subgraph Event Bus
        EB[Event Bus Message Dispatcher]
    end

    subgraph Subscribers
        DB[Database Logger]
        BH[Building Damage Handler]
        TH[Task Generator Handler]
        UI[UI Dashboard Feed]
    end

    WT -->|Publish Event| EB
    ENG -->|Publish Event| EB
    CLI -->|Publish Event| EB

    EB -->|Route Event| DB
    EB -->|Route Event| BH
    EB -->|Route Event| TH
    EB -->|Route Event| UI
```

---

## 2. Event Structure

Every event published to the Event Bus contains a structured payload wrapping details about the trigger:

```python
@dataclass
class Event:
    event_id: str          # Unique UUID
    event_type: str        # E.g., "incident.meteor_strike", "task.completed"
    priority: int          # Propagation order (1: Critical, 5: Low)
    publisher: str         # Module name (e.g., "SIMULATION_ENGINE")
    timestamp: float       # Epoch float
    payload: dict          # Key-value details of the event
```

### Common Event Types & Payloads:

* **`incident.meteor_strike`**:
  * Payload: `{"building_id": 4, "damage_amount": 35, "crater_formed": True}`
* **`task.completed`**:
  * Payload: `{"task_id": 123, "worker_id": 3, "duration_spent": 15}`
* **`resource.depleted`**:
  * Payload: `{"resource_name": "Oxygen", "ticks_at_zero": 1}`

---

## 3. Subscriber Registry & Priority Dispatching

Subscribers register with the Event Bus specifying an Event Type. Multiple subscribers can listen to the same event. To enforce ordered execution (e.g., the *logger* must record the disaster before the *damage handler* modifies values and checks for failure), the Event Bus supports subscription **Priority Tiers**:

```python
class EventBus:
    def __init__(self):
        # Maps event_type -> list of (priority, handler_callback)
        self._subscribers: dict[str, list[tuple[int, Callable]]] = {}

    def subscribe(self, event_type: str, handler: Callable, priority: int = 3) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append((priority, handler))
        # Sort so highest priority (lowest number) is executed first
        self._subscribers[event_type].sort(key=lambda x: x[0])

    def publish(self, event: Event) -> None:
        if event.event_type not in self._subscribers:
            return
        for priority, handler in self._subscribers[event.event_type]:
            # Execute handler synchronously or dispatch to thread pool
            handler(event)
```

---

## 4. Walkthrough: The Meteor Strike Event Chain

Here is a step-by-step trace of a dynamic game incident starting from a random disaster tick to worker dispatch and building restoration:

```mermaid
sequenceDiagram
    autonumber
    participant ENG as Simulation Engine
    participant EB as Event Bus
    participant BH as Building Damage Handler
    participant TH as Task Generator Handler
    participant SCH as Queue Scheduler
    participant WT as Worker Thread (Bob)

    ENG->>EB: publish(incident.meteor_strike)
    Note over EB: Event Bus sorts subscribers by priority
    
    EB->>BH: invoke building_damage_handler(event)
    Note over BH: Deducts 40% durability from Hydroponics Dome
    BH-->>EB: return Success
    
    EB->>TH: invoke task_generator_handler(event)
    Note over TH: Creates 'Repair Hydroponics Dome' Task (Priority: 1)
    TH->>SCH: submit_task(Task_99)
    TH-->>EB: return Success
    
    Note over SCH: Next Queue Evaluation Tick
    SCH->>WT: Assign Task_99 to Worker (Bob)
    
    loop Repairing (5 ticks)
        WT->>WT: Perform work tick
    end
    
    WT->>EB: publish(task.completed)
    
    EB->>BH: invoke building_damage_handler(task.completed)
    Note over BH: Restores health of Hydroponics Dome to 100%
    
    EB->>ENG: notify simulation status is stable
```
