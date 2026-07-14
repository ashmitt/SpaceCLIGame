# 10_TEST_PLAN (Test Plan & Strategy) - ColonyOS

ColonyOS enforces a comprehensive testing matrix to guarantee correctness, thread safety, and scheduling optimization under heavy stress loads. Tests are run using `pytest`.

---

## 1. Unit Testing Strategy

Unit tests isolate single classes and functions, verifying boundary values and schema validation.

### Core Targets:
1. **Scheduler Classes (`FIFOScheduler`, `SJFScheduler`, etc.)**:
   * Verify sorting logic maps exactly to algorithm specifications.
   * Ensure tasks with identical scores fall back to FIFO ordering.
2. **Worker Model (`Worker`)**:
   * Assert energy decay formulas execute correctly.
   * Verify state machine transition guards (e.g., a dead worker cannot accept tasks).
3. **Resource Stockpile calculations**:
   * Verify that resource addition and consumption checks trigger bound guards (preventing negative resource quantities).
4. **Database ORM / DDL integrity**:
   * Validate CRUD actions and index constraints.

---

## 2. Integration Testing Strategy

Integration tests evaluate data flow boundaries between two or more cooperating modules.

### Core Targets:
1. **Event Bus Propagation**:
   * Assert that publishing a `meteor_strike` event registers damage, generates repair tasks, and places the repair task into the Scheduler queue.
2. **Task Assignment Loop**:
   * Verify that the interaction between `Scheduler.next_task()` and `WorkerManager.assign_worker()` atomically transitions the task status to `RUNNING` in the database.
3. **Persistence Save/Load Cycles**:
   * Verify that calling `SaveSystem.save("test_save")` serializes all current workers, buildings, resources, and tasks, and that `SaveSystem.load("test_save")` fully restores the in-memory state.

---

## 3. Simulation & Stress Testing Specifications

To ensure the OS scheduler does not deadlock, starve tasks, or leak memory during long-running sessions, ColonyOS includes a simulation test harness:

### 3.1 Scenario Parameters:
* **Workers**: 20 concurrent threads.
* **Tasks**: 1,000 tasks generated dynamically (mix of building construction, harvesting, and emergency repairs).
* **Simulated Uptime**: 100 simulated hours (equivalent to 100 ticks).
* **Disaster Rate**: 1 random disaster (meteor strike, power surge) triggered every 15 ticks.

### 3.2 Performance Measurement Metrics:
* **Completion Rate**: Must achieve $\ge 95\%$ completion of non-starved tasks.
* **Average Wait Time**: Time from task submission to worker assignment must remain $< 5$ ticks (using SJF/Priority schedulers).
* **Starvation Count**: Total count of tasks that wait $> 50$ ticks must be $0$ (verifies the priority aging daemon works).
* **CPU Usage**: Average CPU time spent in the scheduling evaluation loop must be $< 10\text{ ms}$ per tick.
* **Memory Leaks**: Memory footprint deviation between tick 1 and tick 100 must be $< 2\text{ MB}$.

---

## 4. Mocking Strategy

To keep automated tests fast and deterministic:
* **Clock Mocking**: The real-time background tick daemon is bypassed using a mock tick generator (`unittest.mock`), allowing test loops to manually step ticks forward instantly.
* **User Input Mocking**: CLI commands are pushed programmatically via typer’s `CliRunner` helper, isolating the input interface from prompt blockages.
* **Disaster Randomness Control**: Random number generators (for event triggers and worker injury rates) are seeded using fixed values during test runs to ensure deterministic outputs.

### Test Execution Commands:
```bash
# Run all unit and integration tests
poetry run pytest tests/

# Run the 100-hour simulation stress test specifically
poetry run pytest tests/simulation/test_stress.py --durations=0

# Run tests and generate coverage report
poetry run pytest --cov=src --cov-report=html
```
