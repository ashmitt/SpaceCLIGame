# 02_HLD (High Level Design) - ColonyOS

## 1. System Architecture Overview

ColonyOS uses a modular, decoupled architecture inspired by operating system design. The system runs an event-driven loop and a task queue scheduler, powered by a relational persistence engine.

Here is the high-level architecture diagram showing the components and their boundaries:

```mermaid
graph TD
    CLI[CLI Interpreter / Parser] <--> |Commands & Queries| ENG[Simulation Engine]
    ENG <--> |Ticks / Time Updates| SCH[Scheduler & Task Queue]
    ENG <--> |Pub/Sub Events| BUS[Event Bus]
    ENG <--> |Read/Write State| DB[(SQLite Database)]
    
    SCH <--> |Pulls Tasks / Assigns Workers| WM[Worker Manager]
    WM <--> |Updates Worker State| DB
    SCH <--> |Queries Task Lifecycle| DB
    
    BUS <--> |Disasters / Repairs| SCH
    BUS <--> |Triggers Incidents| ENG
    
    BM[Building Manager] <--> |Durability / Output| ENG
    BM <--> |Resource Demands| RM[Resource Manager]
    RM <--> |Stockpile Math| ENG
    BM <--> |Updates Structures| DB
```

---

## 2. Component Responsibilities

| Component | Responsibility | Interface Library |
| :--- | :--- | :--- |
| **CLI Interpreter** | Parses Unix-style commands, validates arguments, formats outputs using tables, progress bars, and colored logs. | `typer`, `rich`, `prompt_toolkit` |
| **Simulation Engine**| Coordinates the global game clock, triggers the periodic tick cycle, updates resource calculations, and invokes save states. | Python built-ins |
| **Scheduler & Queue** | Manages the task priority queue, evaluates scheduling policies (FIFO, SJF, Priority, Round Robin), and schedules tasks. | `queue.PriorityQueue`, `heapq` |
| **Worker Manager** | Tracks the worker pool state, spawns and coordinates worker threads, handles fatigue/resting timers, and manages skills. | `threading.Thread` |
| **Building Manager** | Manages building inventory, calculates power consumption/production output, and monitors structural durability. | Python OOP |
| **Resource Manager** | Tracks commodity stockpiles (Water, Oxygen, Food, Power) and calculates net accumulation rates per tick. | Python OOP |
| **Event Bus** | A decoupled pub/sub message broker routing incidents, hazards, weather conditions, and structural repairs. | Pub/Sub Pattern |
| **Database Adapter** | Marshals memory objects into SQLite tables and handles atomic queries to prevent file locks. | `sqlite3` (or `SQLAlchemy` ORM) |

---

## 3. Communication & Threading Model

To ensure a highly responsive CLI during game ticks, ColonyOS separates execution into two primary execution spaces:

1. **CLI Process Thread (User Input)**:
   * Runs the interactive prompt loop.
   * Parses user requests.
   * Reads state directly from the SQLite database or cached memory models for instantaneous rendering.
   * Enqueues tasks by writing them into the Database Queue.

2. **Simulation Clock & Worker Daemon Threads (Simulation Core)**:
   * A central **Simulation Clock Thread** ticks once every $1.0\text{ seconds}$ (in real-time mode) or on-demand (in manual mode).
   * **Worker Threads** run in a thread pool. When the Scheduler assigns a task to a worker, a worker thread wakes up, consumes simulated ticks to complete the task, decreases worker energy, and updates the task status in the database.
   * All shared states are synchronized using thread-safe data structures and SQL transaction boundaries to prevent race conditions.

---

## 4. Main System Flows

### 4.1 Task Submission & Execution Sequence

The following diagram traces a player executing a build command through the CLI parser, the database task queue, the scheduler, worker assignment, thread execution, and UI rendering:

```mermaid
sequenceDiagram
    autonumber
    actor Player
    participant CLI as CLI Interpreter
    participant DB as SQLite DB
    participant SCH as Scheduler
    participant WM as Worker Manager
    participant WT as Worker Thread
    participant ENG as Simulation Engine

    Player->>CLI: type "build solar_array"
    CLI->>DB: INSERT INTO tasks (name, priority, duration, status) VALUES ('solar_array', 4, 15, 'PENDING')
    DB-->>CLI: return Task ID #123
    CLI-->>Player: print "Build task submitted (ID: 123)"

    Note over ENG, SCH: Global Clock Tick Event
    ENG->>SCH: trigger_scheduling()
    SCH->>DB: SELECT * FROM tasks WHERE status = 'PENDING'
    DB-->>SCH: list of tasks (including ID #123)
    
    SCH->>SCH: Apply active scheduling algorithm (e.g., SJF)
    SCH->>DB: UPDATE tasks SET status = 'READY' WHERE id = 123
    
    SCH->>WM: get_idle_workers()
    WM->>DB: SELECT * FROM workers WHERE state = 'IDLE'
    DB-->>WM: return Worker_03 (Bob)
    
    SCH->>WM: assign_worker(Worker_03, Task_123)
    WM->>DB: UPDATE tasks SET status = 'RUNNING', worker_id = 3 WHERE id = 123
    WM->>DB: UPDATE workers SET state = 'WORKING' WHERE id = 3
    WM->>WT: wake_up(Task_123)
    
    loop Work Duration (15 ticks)
        WT->>WT: sleep(1 tick interval)
        WT->>DB: UPDATE workers SET energy = energy - 1 WHERE id = 3
    end
    
    WT->>DB: UPDATE tasks SET status = 'COMPLETED', completed_at = CURRENT_TIMESTAMP WHERE id = 123
    WT->>DB: UPDATE workers SET state = 'IDLE' WHERE id = 3
    WT->>ENG: notify_task_complete(Task_123)
    ENG->>DB: INSERT INTO buildings (type, health) VALUES ('solar_array', 100)
    ENG->>CLI: push_dashboard_update()
    CLI-->>Player: Render updated screen (Solar Array active!)
```

### 4.2 Disaster Incident & Cascade Sequence

The flow of an environmental hazard through the Event Bus to task creation:

```mermaid
flowchart TD
    A[Meteor Strike Event Generated] --> B[Publish to Event Bus]
    B --> C[Event Bus notifies Building Damage Handler]
    C --> D[Reduce Solar Array durability by 40%]
    D --> E[Solar Array health < 50%]
    E --> F[Generate Damage Alert Event]
    F --> G[Publish to Event Bus]
    G --> H[Event Bus notifies Task Generator]
    H --> I[Auto-generate Repair Task priority: HIGH]
    I --> J[Submit Task to Queue]
    J --> K[Scheduler assigns Repair Task to Engineer Worker]
```
