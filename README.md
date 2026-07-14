# ColonyOS 🪐

ColonyOS is a terminal-based colony management simulation game where the player acts as the **colony's central operating system** rather than a traditional omnipotent manager. As the OS, you are responsible for task scheduling, queue management, worker assignment, resource allocation, event dispatching, and system persistence.

The simulation runs on a simulated tick rate, using a decoupled event-driven architecture, a relational persistence layer, and a Linux-style CLI interface built using modern Python frameworks.

---

## 🖥️ Terminal Interface Mockup

```text
================================================================================
               ______      __                  ____  _____ 
              / ____/___  / /___  ____  __  __/ __ \/ ___/ 
             / /   / __ \/ / __ \/ __ \/ / / / / / /\__ \  
            / /___/ /_/ / / /_/ / / / / /_/ / /_/ /___/ /  
            \____/\____/_/\____/_/ /_/\__, /\____//____/   
                                     /____/                
================================================================================
  ColonyOS v1.0.0 | Core Status: NOMINAL | Node: Kepler-442b (Habitation Base)
  Uptime: 247 Ticks | Resources: Oxygen: 92% | Energy: 85% | Population: 12/12
================================================================================

[colony@kepler-442b]$ status
--- SYSTEM STATUS ---
Simulation Time: Tick #247
Workers: 12 Active (0 Idle, 2 Resting, 1 Injured)
Power Grid: 140/150 kW (Surplus +10 kW)
Resource Stockpiles:
  - Water:     340 L  (-2.5 L/tick)
  - Food:      890 kg (-1.2 kg/tick)
  - Oxygen:    920 m³ (+0.5 m³/tick)
  - Iron Ore:  120 kg (Stationary)
Buildings:
  - 1x Central Command Hub [Level 1]
  - 1x Hydroponics Dome   [Level 1] (Active)
  - 2x Solar Array        [Level 2] (Generating 80 kW)
  - 1x Water Extractor    [Level 1] (Active)

[colony@kepler-442b]$ queue --list
--- ACTIVE TASK QUEUE (Algorithm: Priority) ---
ID   Priority  Task Name            Duration  Worker Assigned   Status
-------------------------------------------------------------------------
42   1         Repair Solar Array A  8 Ticks   Worker_04 (Bob)   RUNNING
45   2         Harvest Potatoes      15 Ticks  Worker_01 (Alice) RUNNING
48   3         Extract Water         30 Ticks  None              READY
51   5         Refine Iron Ore       10 Ticks  None              PENDING

[colony@kepler-442b]$ build --type solar_array
[SYSTEM] Solar Array construction task submitted to queue (Task ID: 52, Priority: 4).
```

---

## 🚀 Key Features

* **Linux-like command interpreter**: Interact with the colony via typical CLI commands (`status`, `workers`, `queue`, `events`, `jobs`, `build`, `inventory`, `logs`, `help`).
* **Advanced Scheduling Algorithms**: Experience real scheduler logic! Swap scheduling policies dynamically (FIFO, Priority, Shortest Job First (SJF), Deadline, and Round Robin) to optimize productivity.
* **Worker Thread Pool**: Simulate asynchronous task execution where workers (threads) pull jobs from the queue, consume energy, improve skills, rest when fatigued, and report injuries.
* **Pub/Sub Event Bus**: A robust, decoupled event bus that routes game events (solar flares, asteroid hits, system failures) to system handlers, creating cascade repair tasks and environmental hazards.
* **SQLite/SQLAlchemy Database Engine**: Relational storage of game state, saving every worker's attributes, task history, building durability, and log transcripts for seamless session management.

---

## 📂 Project Structure

```text
ColonyOS/
│
├── docs/                             # Engineering & Design Documentation
│   ├── 01_PRD.md                     # Product Requirements Document
│   ├── 02_HLD.md                     # High-Level System Architecture
│   ├── 03_LLD.md                     # Low-Level Code Design
│   ├── 04_DATABASE.md                # SQLite DB Schema & ERD
│   ├── 05_GAME_DESIGN.md             # Game Design, Math & Progression
│   ├── 06_ARCHITECTURE.md            # Architectural Rationale & Patterns
│   ├── 07_TASK_QUEUE.md              # Task Lifecycles & Scheduling Algorithms
│   ├── 08_EVENT_SYSTEM.md            # Event Bus Pub/Sub Specification
│   ├── 09_API.md                     # Module API References
│   ├── 10_TEST_PLAN.md               # Testing Strategy & Scenarios
│   ├── 11_ROADMAP.md                 # Release Timeline & Milestones
│   └── 12_CONTRIBUTING.md            # Code Guidelines & Contributor setup
│
├── src/                              # Application Source Code
│   ├── cli/                          # CLI and Parser Module (typer, rich)
│   ├── core/                         # Simulation Game Engine Loop & Clock
│   ├── scheduler/                    # Task Queue and Schedulers (FIFO, SJF, etc.)
│   ├── event/                        # Pub/Sub Event Bus and Disaster Handlers
│   ├── database/                     # SQLite Database, Models, and Migrations
│   ├── worker/                       # Worker Thread Loop & Behavior Engine
│   └── building/                     # Infrastructure Management & Durability
│
├── tests/                            # Automated Pytest Suite
│   ├── unit/                         # Unit tests for individual classes
│   ├── integration/                  # Component integration tests
│   └── simulation/                   # 100-hour stress simulation tests
│
├── README.md                         # Project Landing Page (This File)
├── pyproject.toml                    # Poetry/Ruff/Black Project Configuration
└── config.yaml                       # Game settings, balancing params, default DB path
```

---

## 🛠️ Technology Stack

| Layer | Technology | Rationale |
| :--- | :--- | :--- |
| **Language** | Python 3.13+ | Leverages modern typing, queue primitives, and SQLite integrations. |
| **CLI & TUI** | `typer` + `rich` | Provides a robust parser for Unix-style arguments and a premium terminal interface. |
| **Data Validation**| `pydantic` | Enforces strong schemas for configuration inputs and network state packets. |
| **Database** | `sqlite3` + `SQLAlchemy` | In-process, single-file relational database ensuring robust serialization. |
| **Concurrency** | `threading` + `queue` | Thread-safe queue structures mapping to simulated worker agents. |
| **Configuration** | `PyYAML` | Human-readable game tuning parameters (durability, energy rates, event weights). |
| **Testing** | `pytest` + `pytest-cov` | Automation framework for unit, integration, and simulation stress testing. |

---

## 📘 Documentation Index

Explore the engineering specifications of ColonyOS:

1. [Product Requirement Document (01_PRD.md)](file:///d:/Projects/SpaceCLIGame/docs/01_PRD.md): Learn about the vision, goals, and user stories.
2. [High-Level Design (02_HLD.md)](file:///d:/Projects/SpaceCLIGame/docs/02_HLD.md): Inspect the macro architecture and inter-module flows.
3. [Low-Level Design (03_LLD.md)](file:///d:/Projects/SpaceCLIGame/docs/03_LLD.md): Class parameters, dependency management, and type schemas.
4. [Database Design (04_DATABASE.md)](file:///d:/Projects/SpaceCLIGame/docs/04_DATABASE.md): SQLite schemas, tables, relationships, and ER diagrams.
5. [Game Design Document (05_GAME_DESIGN.md)](file:///d:/Projects/SpaceCLIGame/docs/05_GAME_DESIGN.md): Formulas, resource consumption, structures, and disaster events.
6. [Architecture Design (06_ARCHITECTURE.md)](file:///d:/Projects/SpaceCLIGame/docs/06_ARCHITECTURE.md): Micro-operating system approach, thread loops, and logging.
7. [Task Queue Design (07_TASK_QUEUE.md)](file:///d:/Projects/SpaceCLIGame/docs/07_TASK_QUEUE.md): Queues, lifecycles, and scheduling algorithms.
8. [Event System Specification (08_EVENT_SYSTEM.md)](file:///d:/Projects/SpaceCLIGame/docs/08_EVENT_SYSTEM.md): Event bus architecture and dynamic trigger cascades.
9. [Module API Reference (09_API.md)](file:///d:/Projects/SpaceCLIGame/docs/09_API.md): Reference API signatures for all core components.
10. [Test Plan (10_TEST_PLAN.md)](file:///d:/Projects/SpaceCLIGame/docs/10_TEST_PLAN.md): Details on testing strategies, mock environments, and stress benchmarks.
11. [Project Roadmap (11_ROADMAP.md)](file:///d:/Projects/SpaceCLIGame/docs/11_ROADMAP.md): Evolutionary targets from prototype to version 1.0.
12. [Contribution Guide (12_CONTRIBUTING.md)](file:///d:/Projects/SpaceCLIGame/docs/12_CONTRIBUTING.md): Setting up formatting (ruff, black), branching, and style.

---

## ⚙️ Installation & Quick Start

### Prerequisites
* Python 3.11+
* Poetry (recommended) or pip with a virtual environment

### Setup
```bash
# Clone the repository
git clone https://github.com/ashmitt/SpaceCLIGame.git
cd SpaceCLIGame

# Option A: Poetry
poetry install
poetry run python main.py

# Option B: pip + venv
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux
pip install typer rich pyyaml pytest pytest-cov ruff black mypy
python main.py
```

You can also launch with `python -m src` or `python -m src.main`.

---

## 🎮 How to Play

You are the **Colony Operating System** on Kepler-442b. Your job is to keep workers alive, balance the power grid, schedule tasks, and expand infrastructure — all through a Linux-style terminal.

### Your First Session (5-Minute Walkthrough)

1. **Launch the game** — run `python main.py` from the project root.
2. **Check colony health** — type `status` to see tick count, resources, buildings, and power balance.
3. **Review your crew** — type `workers` to see Alice, Bob, and Charlie (health, energy, skills, current tasks).
4. **Advance time** — type `tick` to advance one simulated hour, or `wait 10` to skip ahead 10 ticks.
5. **Build power first** — type `build --type SOLAR_ARRAY` to queue a solar array (costs Iron Ore + Solar Cells).
6. **Watch construction** — use `queue` to see the build task; workers will pick it up automatically.
7. **Enable auto-play** — type `daemon start` to run the simulation in real time (1 tick per second by default).
8. **Save progress** — type `save --name my_colony` to copy the database to `my_colony.db`.

### Core Gameplay Loop

Each **tick** (~1 simulated hour) the engine runs this cycle:

1. Buildings generate or consume power
2. Brownouts shut down non-essential buildings if power runs out
3. Workers consume Food, Water, and Oxygen
4. Building durability decays by 1% per tick
5. Active buildings produce resources (Food, Water, Oxygen)
6. Random disaster events may fire
7. Workers progress on assigned tasks
8. State is saved to SQLite

Your colony starts with a **Central Command Hub**, three workers, and starter stockpiles defined in `config.yaml`. Expand carefully — power is the bottleneck.

### Essential Commands

| Command | What it does |
| :--- | :--- |
| `status` | Dashboard: resources, buildings, power grid, tick count |
| `workers` | List all workers with health, energy, skills, and state |
| `queue` | Show the active task queue and current scheduler |
| `queue --set-algo priority` | Switch scheduler (`fifo`, `priority`, `sjf`, `deadline`, `round_robin`) |
| `jobs --add Repair Panel --priority 2 --duration 8` | Inject a custom task into the queue |
| `build --type SOLAR_ARRAY` | Queue construction (see building types below) |
| `tick` | Advance simulation by 1 tick |
| `wait 5` | Advance simulation by N ticks |
| `daemon start` / `daemon stop` | Toggle real-time background ticking |
| `logs 20` | Show the last 20 system log entries |
| `save --name slot1` | Save colony state to `slot1.db` |
| `load --name slot1` | Load a previous save |
| `help` | List all available commands |
| `exit` | Quit the game |

### Building Types

| Type | Purpose | Power | Produces |
| :--- | :--- | :--- | :--- |
| `SOLAR_ARRAY` | Generates power | +40 kW | — |
| `HYDROPONICS_DOME` | Grows food | −20 kW | +4 Food/tick |
| `WATER_EXTRACTOR` | Extracts water | −15 kW | +8 Water/tick |
| `LIFE_SUPPORT` | Generates oxygen | −30 kW | +10 Oxygen/tick |
| `COMMAND_HUB` | Starter base (cannot build) | −10 kW | — |

Build order tip: **Solar Array → Water Extractor → Hydroponics Dome → Life Support**. Without solar power, brownouts will disable your production buildings.

### Scheduling Strategies

Workers pull tasks from the queue using the active algorithm:

* **fifo** — first in, first out; simple and predictable
* **priority** — lower number = higher priority (default)
* **sjf** — shortest jobs finish first; good for quick repairs
* **deadline** — tasks closest to their deadline run first
* **round_robin** — fair time-slicing across tasks

Swap mid-game with `queue --set-algo sjf` when your colony needs to adapt.

### Survival Tips

* **Watch Oxygen and Power** — if either hits zero, workers lose health fast.
* **Repair before collapse** — buildings at 0% health stop working; efficiency scales with health below 50%.
* **Use `daemon start`** for hands-off play, **`tick`/`wait`** for precise control.
* **Check `logs`** after disasters — solar flares and power surges can cascade into repair tasks.
* **Experiment with schedulers** — a bad queue policy can starve critical repairs during a crisis.

### Win & Lose Conditions

**You lose if:**
* All workers die
* The Central Command Hub is destroyed (0% health)
* Oxygen stays at 0 for 15 consecutive ticks

**You win by** researching advanced tech, building an Atmosphere Stabilizer, and maintaining colony integrity for 50 ticks (see [Game Design Doc](docs/05_GAME_DESIGN.md) for full details).

---

### CLI Command Summary
* `status` - Get colony vital statistics, resource rates, and active buildings.
* `workers` - List active workers, health, energy levels, and current tasks.
* `queue --set-algo <algo>` - Change active scheduler algorithm (e.g., `sjf`, `priority`, `round_robin`).
* `jobs --add <name> --priority <p>` - Inject a custom task into the colony queue.
* `build --type <type>` - Schedule a building construction project.
* `save --name <save_name>` - Write the active database/state to a save file.
* `logs` - View historical event and task output logs.
