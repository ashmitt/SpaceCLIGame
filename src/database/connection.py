import sqlite3
import threading
from contextlib import contextmanager
from typing import Any, List, Optional, Tuple


class DBHelper:
    _lock = threading.Lock()
    _instance: Optional["DBHelper"] = None

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DBHelper, cls).__new__(cls)
            return cls._instance

    def __init__(self, db_path: str = "colony.db"):
        # Prevent re-initialization if already done
        if hasattr(self, "initialized"):
            return
        self.db_path = db_path
        self.initialized = True
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # Enable WAL mode
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    @contextmanager
    def transaction(self):
        """Context manager for executing transactions with a shared lock."""
        with self._lock:
            conn = self.get_connection()
            try:
                yield conn
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                conn.close()

    def execute(self, query: str, params: Optional[Tuple[Any, ...]] = None) -> int:
        """Executes a single write query and returns the lastrowid."""
        with self._lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                conn.commit()
                rowid = cursor.lastrowid or 0
                return rowid
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                conn.close()

    def execute_many(self, query: str, params_list: List[Tuple[Any, ...]]) -> None:
        """Executes multiple write queries under a lock."""
        with self._lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            try:
                cursor.executemany(query, params_list)
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                conn.close()

    def fetch_all(self, query: str, params: Optional[Tuple[Any, ...]] = None) -> List[sqlite3.Row]:
        """Fetches all rows for a query under a lock."""
        with self._lock:
            conn = self.get_connection()
            try:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                rows = cursor.fetchall()
                return rows
            finally:
                conn.close()

    def fetch_one(
        self, query: str, params: Optional[Tuple[Any, ...]] = None
    ) -> Optional[sqlite3.Row]:
        """Fetches a single row for a query under a lock."""
        with self._lock:
            conn = self.get_connection()
            try:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                row = cursor.fetchone()
                return row
            finally:
                conn.close()

    def init_db(self):
        """Initializes database tables, indices, and defaults."""
        with self._lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            try:
                # 1. workers table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS workers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    health INTEGER DEFAULT 100 CHECK (health BETWEEN 0 AND 100),
                    energy INTEGER DEFAULT 100 CHECK (energy BETWEEN 0 AND 100),
                    experience INTEGER DEFAULT 0,
                    skill_construction INTEGER DEFAULT 1,
                    skill_agriculture INTEGER DEFAULT 1,
                    skill_engineering INTEGER DEFAULT 1,
                    current_task_id INTEGER,
                    state TEXT DEFAULT 'IDLE' CHECK (state IN ('IDLE', 'WORKING', 'RESTING', 'FATIGUED', 'INJURED', 'DEAD'))
                );
                """)

                # 2. tasks table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    priority INTEGER DEFAULT 3 CHECK (priority BETWEEN 1 AND 5),
                    duration INTEGER NOT NULL,
                    remaining_duration INTEGER NOT NULL,
                    worker_id INTEGER,
                    status TEXT DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'READY', 'RUNNING', 'COMPLETED', 'FAILED', 'RETRY', 'DEAD')),
                    retry_count INTEGER DEFAULT 0,
                    dependencies TEXT, -- Comma separated task IDs
                    deadline INTEGER,
                    created_tick INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    started_at TEXT,
                    completed_at TEXT
                );
                """)

                # 3. buildings table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS buildings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL CHECK (type IN ('COMMAND_HUB', 'HYDROPONICS_DOME', 'SOLAR_ARRAY', 'WATER_EXTRACTOR', 'LIFE_SUPPORT')),
                    level INTEGER DEFAULT 1,
                    health INTEGER DEFAULT 100 CHECK (health BETWEEN 0 AND 100),
                    efficiency REAL DEFAULT 1.0,
                    active INTEGER DEFAULT 1
                );
                """)

                # 4. resources table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS resources (
                    name TEXT PRIMARY KEY CHECK (name IN ('Water', 'Food', 'Oxygen', 'Power', 'IronOre', 'SolarCells')),
                    amount REAL DEFAULT 0.0,
                    capacity REAL DEFAULT 100.0
                );
                """)

                # 5. game_state table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS game_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """)

                # 6. research table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS research (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    unlocked INTEGER DEFAULT 0,
                    cost REAL NOT NULL,
                    cost_type TEXT NOT NULL
                );
                """)

                # 7. events table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    trigger_tick INTEGER NOT NULL,
                    severity TEXT NOT NULL,
                    resolved INTEGER DEFAULT 0,
                    type TEXT NOT NULL,
                    details TEXT
                );
                """)

                # 8. logs table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    module TEXT NOT NULL
                );
                """)

                # Indices
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_tasks_status_priority ON tasks (status, priority);"
                )
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_workers_state ON workers (state);")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs (timestamp DESC);"
                )

                conn.commit()
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                conn.close()
