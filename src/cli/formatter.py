import sqlite3

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


class CLIFormatter:
    @staticmethod
    def print_dashboard(conn: sqlite3.Connection) -> None:
        """Renders the main system status dashboard."""
        # Query status
        tick_row = conn.execute(
            "SELECT value FROM game_state WHERE key = 'current_tick'"
        ).fetchone()
        algo_row = conn.execute(
            "SELECT value FROM game_state WHERE key = 'active_scheduler'"
        ).fetchone()
        status_row = conn.execute("SELECT value FROM game_state WHERE key = 'game_over'").fetchone()

        tick = tick_row["value"] if tick_row else "1"
        algo = (algo_row["value"] if algo_row else "priority").upper()
        status = (status_row["value"] if status_row else "RUNNING").upper()

        status_color = (
            "green" if status == "RUNNING" else ("cyan" if status == "VICTORY" else "red")
        )

        console.print(
            Panel(
                f"[bold yellow]ColonyOS v1.0.0[/bold yellow] | "
                f"Simulation Time: [bold cyan]Tick #{tick}[/bold cyan] | "
                f"Core Status: [bold {status_color}]{status}[/bold {status_color}] | "
                f"Scheduler Policy: [bold magenta]{algo}[/bold magenta]",
                title="🪐 Colony Terminal",
                border_style="cyan",
            )
        )

        # Resources Table
        res_rows = conn.execute("SELECT * FROM resources").fetchall()
        res_table = Table(
            title="📦 Resource Stockpiles",
            title_style="bold yellow",
            show_header=True,
            header_style="bold blue",
        )
        res_table.add_column("Resource")
        res_table.add_column("Amount / Capacity")
        res_table.add_column("Fill Level")

        for r in res_rows:
            amount = r["amount"]
            capacity = r["capacity"]
            ratio = amount / capacity if capacity > 0 else 0

            # Simple color formatting based on ratio
            color = "green" if ratio > 0.5 else ("yellow" if ratio > 0.2 else "red")
            bar = "█" * int(ratio * 15) + "░" * (15 - int(ratio * 15))

            res_table.add_row(
                r["name"],
                f"[{color}]{amount:.1f} / {capacity:.1f}[/{color}]",
                f"[{color}]{bar} ({ratio*100:.1f}%)[/{color}]",
            )

        # Buildings Table
        b_rows = conn.execute("SELECT * FROM buildings").fetchall()
        b_table = Table(
            title="🏢 Infrastructure Registry",
            title_style="bold yellow",
            show_header=True,
            header_style="bold blue",
        )
        b_table.add_column("ID", style="dim")
        b_table.add_column("Name")
        b_table.add_column("Type")
        b_table.add_column("Level")
        b_table.add_column("Durability")
        b_table.add_column("State")

        for b in b_rows:
            active = "[green]ACTIVE[/green]" if b["active"] == 1 else "[yellow]OFFLINE[/yellow]"
            health = b["health"]
            h_color = "green" if health > 75 else ("yellow" if health > 30 else "red")

            b_table.add_row(
                str(b["id"]),
                b["name"],
                b["type"],
                f"Lvl {b['level']}",
                f"[{h_color}]{health}%[/{h_color}]",
                active,
            )

        console.print(res_table)
        console.print(b_table)

    @staticmethod
    def print_queue(conn: sqlite3.Connection) -> None:
        """Renders the active task queue."""
        rows = conn.execute("""
            SELECT t.*, w.name as worker_name 
            FROM tasks t 
            LEFT JOIN workers w ON t.worker_id = w.id 
            WHERE t.status NOT IN ('COMPLETED', 'DEAD')
            ORDER BY t.status DESC, t.priority ASC, t.id ASC
            """).fetchall()

        table = Table(
            title="📥 Active Task Queue",
            title_style="bold yellow",
            show_header=True,
            header_style="bold blue",
        )
        table.add_column("ID", style="dim")
        table.add_column("Priority")
        table.add_column("Task Description")
        table.add_column("Ticks Left")
        table.add_column("Assigned Worker")
        table.add_column("Status")
        table.add_column("Deadline")

        for r in rows:
            status = r["status"]
            s_color = (
                "yellow" if status == "PENDING" else ("cyan" if status == "READY" else "green")
            )

            worker = r["worker_name"] if r["worker_name"] else "[dim]None[/dim]"
            priority = f"P{r['priority']}"
            deadline = f"Tick {r['deadline']}" if r["deadline"] is not None else "[dim]None[/dim]"

            table.add_row(
                str(r["id"]),
                priority,
                r["name"],
                f"{r['remaining_duration']} / {r['duration']} ticks",
                worker,
                f"[{s_color}]{status}[/{s_color}]",
                deadline,
            )

        console.print(table)

    @staticmethod
    def print_workers(conn: sqlite3.Connection) -> None:
        """Renders the worker pool attributes."""
        rows = conn.execute("""
            SELECT w.*, t.name as task_name 
            FROM workers w 
            LEFT JOIN tasks t ON w.current_task_id = t.id
            """).fetchall()

        table = Table(
            title="👥 Colonist Roster",
            title_style="bold yellow",
            show_header=True,
            header_style="bold blue",
        )
        table.add_column("ID", style="dim")
        table.add_column("Name")
        table.add_column("Health")
        table.add_column("Energy")
        table.add_column("Construction / Agri / Eng")
        table.add_column("State")
        table.add_column("Current Task")

        for r in rows:
            state = r["state"]
            st_color = "green" if state == "IDLE" else ("yellow" if state == "WORKING" else "cyan")
            if state in ("FATIGUED", "INJURED"):
                st_color = "red"
            elif state == "DEAD":
                st_color = "dim red"

            health = f"[{'green' if r['health'] > 50 else 'red'}]{r['health']}%[/{'green' if r['health'] > 50 else 'red'}]"
            energy = f"[{'green' if r['energy'] > 30 else 'red'}]{r['energy']}%[/{'green' if r['energy'] > 30 else 'red'}]"
            skills = f"Lvl {r['skill_construction']} / Lvl {r['skill_agriculture']} / Lvl {r['skill_engineering']}"
            task = r["task_name"] if r["task_name"] else "[dim]Idle[/dim]"

            table.add_row(
                str(r["id"]),
                r["name"],
                health,
                energy,
                skills,
                f"[{st_color}]{state}[/{st_color}]",
                task,
            )

        console.print(table)

    @staticmethod
    def print_logs(conn: sqlite3.Connection, limit: int = 10) -> None:
        """Renders the historical system logs."""
        rows = conn.execute("SELECT * FROM logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()

        table = Table(
            title="📜 Syslog Audit Records",
            title_style="bold yellow",
            show_header=True,
            header_style="bold blue",
        )
        table.add_column("Timestamp")
        table.add_column("Level")
        table.add_column("Module")
        table.add_column("Message Log")

        for r in rows:
            level = r["level"]
            lvl_color = "green" if level == "INFO" else ("yellow" if level == "WARNING" else "red")
            if level == "CRITICAL":
                lvl_color = "bold white on red"

            table.add_row(
                r["timestamp"], f"[{lvl_color}]{level}[/{lvl_color}]", r["module"], r["message"]
            )

        console.print(table)
