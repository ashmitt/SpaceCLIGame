import cmd
import logging
import os
import shutil

from src.cli.formatter import CLIFormatter
from src.core.engine import SimulationEngine
from src.scheduler.models import Task, TaskStatus
from src.event.models import Event

logger = logging.getLogger("ColonyOS.Shell")


class ColonyShell(cmd.Cmd):
    prompt = "[colony@kepler-442b]$ "
    intro = (
        "\n"
        "================================================================================\n"
        "               ______      __                  ____  _____ \n"
        "              / ____/___  / /___  ____  __  __/ __ \\/ ___/ \n"
        "             / /   / __ \\/ / __ \\/ __ \\/ / / / / / /\\__ \\  \n"
        "            / /___/ /_/ / / /_/ / / / / /_/ / /_/ /___/ /  \n"
        "            \\____/\\____/_/\\____/_/ /_/\\__, /\\____//____/   \n"
        "                                     /____/                \n"
        "================================================================================\n"
        "  ColonyOS v1.0.0 Interface Active | Node: Kepler-442b (Habitation Base)\n"
        "  Welcome to the central operating command console.\n"
        "  Type 'help' or 'status' to review instructions.\n"
        "================================================================================\n"
    )

    def __init__(self, engine: SimulationEngine):
        super().__init__()
        self.engine = engine
        self.db = engine.db

    def emptyline(self) -> bool:
        # Prevent repeating previous command on empty line
        return False

    def do_status(self, arg: str) -> None:
        """View vital statistics, resource stockpiles, and buildings."""
        with self.db.transaction() as conn:
            CLIFormatter.print_dashboard(conn)

    def do_workers(self, arg: str) -> None:
        """List active colony workers, their health, energy, skills, and states."""
        with self.db.transaction() as conn:
            CLIFormatter.print_workers(conn)

    def do_queue(self, arg: str) -> None:
        """
        View task queue or change active scheduling algorithm.
        Usage:
          queue                  - List active task queue
          queue --set-algo <alg> - Swaps policy (fifo, priority, sjf, deadline, round_robin)
        """
        args = arg.strip().split()
        if not args:
            with self.db.transaction() as conn:
                CLIFormatter.print_queue(conn)
            return

        if len(args) >= 2 and (args[0] == "--set-algo" or args[0] == "-set-algo"):
            algo = args[1].lower()
            try:
                self.engine.scheduler.set_policy(algo)
                print(f"[SYSTEM] Swapped active scheduler policy to '{algo.upper()}'.")
            except ValueError as e:
                print(f"[ERROR] {e}")
        else:
            print("[ERROR] Invalid queue command. See 'help queue'.")

    def do_jobs(self, arg: str) -> None:
        """
        Injects a custom task into the colony queue.
        Usage:
          jobs --add <name> --priority <1-5> --duration <ticks> [--deadline <ticks>]
        """
        args = arg.strip().split()
        if not args or args[0] != "--add":
            print(
                "[ERROR] Invalid command. Usage: jobs --add <name> --priority <1-5> --duration <ticks>"
            )
            return

        try:
            # Simple manual parse of args list
            name = "Manual Job"
            priority = 3
            duration = 5
            deadline = None

            # Look for flags
            for i in range(len(args)):
                if args[i] == "--add" and i + 1 < len(args):
                    # Gather name until next flag
                    name_parts = []
                    idx = i + 1
                    while idx < len(args) and not args[idx].startswith("--"):
                        name_parts.append(args[idx])
                        idx += 1
                    name = " ".join(name_parts).replace('"', "")
                elif args[i] == "--priority" and i + 1 < len(args):
                    priority = int(args[i + 1])
                elif args[i] == "--duration" and i + 1 < len(args):
                    duration = int(args[i + 1])
                elif args[i] == "--deadline" and i + 1 < len(args):
                    deadline = int(args[i + 1])

            task = Task(
                id=None,
                name=name,
                priority=priority,
                duration=duration,
                remaining_duration=duration,
                status=TaskStatus.PENDING,
                deadline=deadline,
            )
            self.engine.scheduler.submit_task(task)
            print(f"[SYSTEM] Job '{name}' added to task queue.")
        except Exception as e:
            print(f"[ERROR] Failed to parse and add job: {e}")

    def do_build(self, arg: str) -> None:
        """
        Submits a construction task to build colony structures.
        Usage:
          build --type <COMMAND_HUB|SOLAR_ARRAY|HYDROPONICS_DOME|WATER_EXTRACTOR|LIFE_SUPPORT>
        """
        args = arg.strip().split()
        if not args or args[0] != "--type" or len(args) < 2:
            print("[ERROR] Usage: build --type <building_type>")
            return

        b_type = args[1].upper().strip()
        b_meta = self.engine.config.get("buildings", {})
        if b_type not in b_meta:
            print(f"[ERROR] Invalid building type. Choices: {list(b_meta.keys())}")
            return

        meta = b_meta[b_type]
        cost = meta.get("construction_cost", {})

        # Verify resources
        with self.db.transaction() as conn:
            # Check availability
            for name, needed in cost.items():
                row = conn.execute(
                    "SELECT amount FROM resources WHERE name = ?", (name,)
                ).fetchone()
                if not row or row["amount"] < needed:
                    print(
                        f"[ERROR] Insufficient '{name}'. Needed: {needed}, Available: {row['amount'] if row else 0}"
                    )
                    return

            # Deduct resources
            for name, needed in cost.items():
                conn.execute(
                    "UPDATE resources SET amount = amount - ? WHERE name = ?", (needed, name)
                )

        # Add construction task to queue
        task_name = f"Build {meta['name']}"
        task = Task(
            id=None,
            name=task_name,
            priority=4,  # building construction priority = 4
            duration=10,  # Construction takes 10 ticks
            remaining_duration=10,
            status=TaskStatus.PENDING,
        )
        task_id = self.engine.scheduler.submit_task(task)

        # Subscribe completion trigger to EventBus (creates the building row upon completion)
        def on_construction_complete(event: Event):
            if event.payload.get("task_id") == task_id:
                self.db.execute(
                    "INSERT INTO buildings (name, type, level, health, efficiency, active) VALUES (?, ?, 1, 100, 1.0, 1)",
                    (meta["name"], b_type),
                )
                print(f"\n[EVENT] Construction completed! Building '{meta['name']}' is now online.")
                self.engine.event_bus.unsubscribe("task.completed", on_construction_complete)

        self.engine.event_bus.subscribe("task.completed", on_construction_complete, priority=1)
        print(f"[SYSTEM] Building construction task submitted (ID: {task_id}). Cost deducted.")

    def do_tick(self, arg: str) -> None:
        """Advance the simulation clock by 1 tick manually."""
        print("[SYSTEM] Ticking clock...")
        self.engine.tick()
        self.do_status(None)

    def do_wait(self, arg: str) -> None:
        """Advance simulation forward by a specified number of ticks. Usage: wait <N>"""
        if not arg.strip():
            print("[ERROR] Specify number of ticks. E.g., 'wait 5'")
            return
        try:
            ticks = int(arg.strip())
            print(f"[SYSTEM] Ticking clock forward {ticks} ticks...")
            for _ in range(ticks):
                self.engine.tick()
            self.do_status(None)
        except ValueError:
            print("[ERROR] Ticks must be an integer.")

    def do_daemon(self, arg: str) -> None:
        """
        Manage the background real-time simulation ticking loop.
        Usage:
          daemon start - Starts automatic ticks
          daemon stop  - Halts automatic ticks
        """
        cmd = arg.strip().lower()
        if cmd == "start":
            self.engine.start_daemon()
            print("[SYSTEM] Background ticking loop started.")
        elif cmd == "stop":
            self.engine.stop_daemon()
            print("[SYSTEM] Background ticking loop stopped.")
        else:
            print("[ERROR] Usage: daemon <start|stop>")

    def do_logs(self, arg: str) -> None:
        """View historical system logs."""
        limit = 10
        if arg.strip():
            try:
                limit = int(arg.strip())
            except ValueError:
                pass
        with self.db.transaction() as conn:
            CLIFormatter.print_logs(conn, limit)

    def do_save(self, arg: str) -> None:
        """Save the active colony state. Usage: save --name <save_name>"""
        args = arg.strip().split()
        if not args or args[0] != "--name" or len(args) < 2:
            print("[ERROR] Usage: save --name <save_name>")
            return

        save_name = args[1].strip()
        save_file = f"{save_name}.db"
        try:
            # Clean up db WAL writes before copying
            self.db.execute("PRAGMA checkpoint_truncate;")
            shutil.copyfile(self.db.db_path, save_file)
            print(f"[SYSTEM] Saved colony state to '{save_file}' successfully.")
        except Exception as e:
            print(f"[ERROR] Failed to save database: {e}")

    def do_load(self, arg: str) -> None:
        """Load a previous colony save state. Usage: load --name <save_name>"""
        args = arg.strip().split()
        if not args or args[0] != "--name" or len(args) < 2:
            print("[ERROR] Usage: load --name <save_name>")
            return

        save_name = args[1].strip()
        save_file = f"{save_name}.db"
        if not os.path.exists(save_file):
            print(f"[ERROR] Save file '{save_file}' does not exist.")
            return

        # Halt background processing before copying over active database
        was_daemon = self.engine.is_running_daemon
        if was_daemon:
            self.engine.stop_daemon()
        else:
            self.engine.worker_mgr.stop_workers()

        try:
            shutil.copyfile(save_file, self.db.db_path)
            print(f"[SYSTEM] Loaded colony state from '{save_file}' successfully.")
        except Exception as e:
            print(f"[ERROR] Failed to load save file: {e}")
        finally:
            # Restart
            if was_daemon:
                self.engine.start_daemon()
            else:
                self.engine.worker_mgr.start_workers()

    def do_exit(self, arg: str) -> bool:
        """Halts the Command Shell interface and stops worker daemon loops."""
        print("[SYSTEM] Shutting down ColonyOS. Safe travels...")
        self.engine.stop_daemon()
        return True

    def do_EOF(self, arg: str) -> bool:
        print("")
        return self.do_exit(arg)
