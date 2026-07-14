# ColonyOS commit bootstrap script — creates granular initial history
$ErrorActionPreference = "Stop"
Set-Location "d:\Projects\SpaceCLIGame"

$env:GIT_AUTHOR_NAME = "ashmitt"
$env:GIT_AUTHOR_EMAIL = "ashmitrai0905@gmail.com"
$env:GIT_COMMITTER_NAME = "ashmitt"
$env:GIT_COMMITTER_EMAIL = "ashmitrai0905@gmail.com"

function Commit-Files {
    param([string]$Message, [string[]]$Files)
    git add @Files
    git commit -m $Message
}

git init -b main

Commit-Files "chore: add gitignore for Python, venv, and runtime artifacts" @(".gitignore")
Commit-Files "chore: add Poetry project configuration and dev tooling" @("pyproject.toml")
Commit-Files "chore: add default game configuration and balancing parameters" @("config.yaml")

Commit-Files "feat(database): add SQLite connection helper and schema initialization" @("src/database/connection.py")

Commit-Files "feat(event): add event model definitions" @("src/event/models.py")
Commit-Files "feat(event): add pub/sub event bus implementation" @("src/event/bus.py")
Commit-Files "feat(event): add game event handlers for disasters and cascades" @("src/event/handlers.py")

Commit-Files "feat(scheduler): add task models and status enums" @("src/scheduler/models.py")
Commit-Files "feat(scheduler): add FIFO, priority, SJF, deadline, and round-robin algorithms" @("src/scheduler/algorithms.py")
Commit-Files "feat(scheduler): add scheduler core with policy switching" @("src/scheduler/core.py")

Commit-Files "feat(core): add resource manager for stockpile tracking" @("src/core/resources.py")
Commit-Files "feat(building): add building manager with power grid and production" @("src/building/manager.py")

Commit-Files "feat(worker): add worker thread simulation loop" @("src/worker/thread.py")
Commit-Files "feat(worker): add worker manager and thread pool coordination" @("src/worker/manager.py")

Commit-Files "feat(core): add simulation engine with tick loop and daemon mode" @("src/core/engine.py")

Commit-Files "feat(cli): add Rich-based terminal formatter for dashboards" @("src/cli/formatter.py")
Commit-Files "feat(cli): add interactive command shell with colony commands" @("src/cli/shell.py")

Commit-Files "feat: add application entry point with project-root path resolution" @("src/main.py")

Commit-Files "docs: add product requirements document" @("docs/01_PRD.md")
Commit-Files "docs: add high-level system design" @("docs/02_HLD.md")
Commit-Files "docs: add low-level code design" @("docs/03_LLD.md")
Commit-Files "docs: add database schema and ERD documentation" @("docs/04_DATABASE.md")
Commit-Files "docs: add game design formulas and progression tree" @("docs/05_GAME_DESIGN.md")
Commit-Files "docs: add architecture rationale and patterns" @("docs/06_ARCHITECTURE.md")
Commit-Files "docs: add task queue and scheduling algorithm specification" @("docs/07_TASK_QUEUE.md")
Commit-Files "docs: add event system pub/sub specification" @("docs/08_EVENT_SYSTEM.md")
Commit-Files "docs: add module API reference" @("docs/09_API.md")
Commit-Files "docs: add testing strategy and scenarios" @("docs/10_TEST_PLAN.md")
Commit-Files "docs: add project roadmap and milestones" @("docs/11_ROADMAP.md")
Commit-Files "docs: add contributor setup and coding standards" @("docs/12_CONTRIBUTING.md")

Commit-Files "test: add scheduler unit tests" @("tests/unit/test_scheduler.py")
Commit-Files "test: add event flow integration tests" @("tests/integration/test_event_flow.py")
Commit-Files "test: add long-running stress simulation tests" @("tests/simulation/test_stress.py")

Commit-Files "feat: add root and module entry points for flexible launch" @("main.py", "src/__main__.py")
Commit-Files "docs: add README with gameplay guide and installation instructions" @("README.md")

Write-Host "`nDone. $(git rev-list --count HEAD) commits created."
