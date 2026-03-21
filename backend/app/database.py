"""
Database layer for MiroFish.
Provides SQLite-backed persistence for tasks, projects, simulations, and reports.
"""

import os
import json
import sqlite3
import threading
from typing import Optional, List, Dict, Any

from .config import Config
from .utils.logger import get_logger

logger = get_logger('mirofish.database')

# Schema version for migrations
SCHEMA_VERSION = 1

SCHEMA_SQL = """
-- Tasks (replaces in-memory TaskManager dict)
CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    task_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    progress INTEGER DEFAULT 0,
    message TEXT DEFAULT '',
    result TEXT,
    error TEXT,
    metadata TEXT,
    progress_detail TEXT
);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at);

-- Projects (replaces per-project project.json)
CREATE TABLE IF NOT EXISTS projects (
    project_id TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT 'Unnamed Project',
    status TEXT NOT NULL DEFAULT 'created',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    total_text_length INTEGER DEFAULT 0,
    ontology TEXT,
    analysis_summary TEXT,
    graph_id TEXT,
    graph_build_task_id TEXT,
    simulation_requirement TEXT,
    chunk_size INTEGER DEFAULT 500,
    chunk_overlap INTEGER DEFAULT 50,
    error TEXT,
    files TEXT
);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_projects_created ON projects(created_at);

-- Simulations (replaces per-simulation state.json)
CREATE TABLE IF NOT EXISTS simulations (
    simulation_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    graph_id TEXT NOT NULL,
    enable_twitter BOOLEAN DEFAULT 1,
    enable_reddit BOOLEAN DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'created',
    entities_count INTEGER DEFAULT 0,
    profiles_count INTEGER DEFAULT 0,
    entity_types TEXT,
    config_generated BOOLEAN DEFAULT 0,
    config_reasoning TEXT DEFAULT '',
    current_round INTEGER DEFAULT 0,
    twitter_status TEXT DEFAULT 'not_started',
    reddit_status TEXT DEFAULT 'not_started',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    error TEXT
);
CREATE INDEX IF NOT EXISTS idx_simulations_project ON simulations(project_id);
CREATE INDEX IF NOT EXISTS idx_simulations_status ON simulations(status);
CREATE INDEX IF NOT EXISTS idx_simulations_created ON simulations(created_at);

-- Reports (replaces per-report meta.json)
CREATE TABLE IF NOT EXISTS reports (
    report_id TEXT PRIMARY KEY,
    simulation_id TEXT NOT NULL,
    graph_id TEXT NOT NULL,
    simulation_requirement TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    outline TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT DEFAULT '',
    error TEXT
);
CREATE INDEX IF NOT EXISTS idx_reports_simulation ON reports(simulation_id);
CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);
"""


class Database:
    """
    Thread-safe SQLite database wrapper (singleton).
    Uses per-thread connections via threading.local().
    """

    _instance = None
    _init_lock = threading.Lock()

    def __new__(cls, db_path: Optional[str] = None):
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._db_path = db_path or Config.DB_PATH
                    instance._local = threading.local()
                    instance._write_lock = threading.Lock()
                    cls._instance = instance
        return cls._instance

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create a per-thread connection."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn = conn
        return self._local.conn

    def init_db(self):
        """Initialize database schema and run migrations."""
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)

        conn = self._get_connection()
        with self._write_lock:
            conn.executescript(SCHEMA_SQL)

            # Check and record schema version
            cursor = conn.execute(
                "SELECT MAX(version) FROM schema_version"
            )
            row = cursor.fetchone()
            current_version = row[0] if row[0] is not None else 0

            if current_version < SCHEMA_VERSION:
                from datetime import datetime
                conn.execute(
                    "INSERT OR REPLACE INTO schema_version (version, applied_at) VALUES (?, ?)",
                    (SCHEMA_VERSION, datetime.now().isoformat())
                )
                conn.commit()

                # Run one-time migration from files if DB was just created
                if current_version == 0:
                    self._migrate_from_files()

        logger.info(f"Database initialized at {self._db_path}")

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a write query with thread-safe locking."""
        conn = self._get_connection()
        with self._write_lock:
            cursor = conn.execute(sql, params)
            conn.commit()
            return cursor

    def executemany(self, sql: str, params_list: List[tuple]) -> sqlite3.Cursor:
        """Execute many write queries with thread-safe locking."""
        conn = self._get_connection()
        with self._write_lock:
            cursor = conn.executemany(sql, params_list)
            conn.commit()
            return cursor

    def fetchone(self, sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """Execute a read query and return one row."""
        conn = self._get_connection()
        cursor = conn.execute(sql, params)
        return cursor.fetchone()

    def fetchall(self, sql: str, params: tuple = ()) -> List[sqlite3.Row]:
        """Execute a read query and return all rows."""
        conn = self._get_connection()
        cursor = conn.execute(sql, params)
        return cursor.fetchall()

    def _migrate_from_files(self):
        """One-time migration: import existing JSON data into SQLite."""
        logger.info("Running one-time migration from file-based storage...")

        projects_migrated = self._migrate_projects()
        simulations_migrated = self._migrate_simulations()
        reports_migrated = self._migrate_reports()

        logger.info(
            f"Migration complete: {projects_migrated} projects, "
            f"{simulations_migrated} simulations, {reports_migrated} reports"
        )

    def _migrate_projects(self) -> int:
        """Migrate projects from project.json files."""
        projects_dir = os.path.join(Config.UPLOAD_FOLDER, 'projects')
        if not os.path.exists(projects_dir):
            return 0

        count = 0
        conn = self._get_connection()
        for project_id in os.listdir(projects_dir):
            meta_path = os.path.join(projects_dir, project_id, 'project.json')
            if not os.path.exists(meta_path):
                continue
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                conn.execute(
                    """INSERT OR IGNORE INTO projects
                    (project_id, name, status, created_at, updated_at,
                     total_text_length, ontology, analysis_summary, graph_id,
                     graph_build_task_id, simulation_requirement, chunk_size,
                     chunk_overlap, error, files)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        data.get('project_id', project_id),
                        data.get('name', 'Unnamed Project'),
                        data.get('status', 'created'),
                        data.get('created_at', ''),
                        data.get('updated_at', ''),
                        data.get('total_text_length', 0),
                        json.dumps(data.get('ontology')) if data.get('ontology') else None,
                        data.get('analysis_summary'),
                        data.get('graph_id'),
                        data.get('graph_build_task_id'),
                        data.get('simulation_requirement'),
                        data.get('chunk_size', 500),
                        data.get('chunk_overlap', 50),
                        data.get('error'),
                        json.dumps(data.get('files', [])),
                    )
                )
                count += 1
            except Exception as e:
                logger.warning(f"Failed to migrate project {project_id}: {e}")
        conn.commit()
        return count

    def _migrate_simulations(self) -> int:
        """Migrate simulations from state.json files."""
        sims_dir = os.path.join(Config.UPLOAD_FOLDER, 'simulations')
        if not os.path.exists(sims_dir):
            return 0

        count = 0
        conn = self._get_connection()
        for sim_id in os.listdir(sims_dir):
            state_path = os.path.join(sims_dir, sim_id, 'state.json')
            if not os.path.exists(state_path):
                continue
            try:
                with open(state_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                conn.execute(
                    """INSERT OR IGNORE INTO simulations
                    (simulation_id, project_id, graph_id, enable_twitter, enable_reddit,
                     status, entities_count, profiles_count, entity_types,
                     config_generated, config_reasoning, current_round,
                     twitter_status, reddit_status, created_at, updated_at, error)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        data.get('simulation_id', sim_id),
                        data.get('project_id', ''),
                        data.get('graph_id', ''),
                        data.get('enable_twitter', True),
                        data.get('enable_reddit', True),
                        data.get('status', 'created'),
                        data.get('entities_count', 0),
                        data.get('profiles_count', 0),
                        json.dumps(data.get('entity_types', [])),
                        data.get('config_generated', False),
                        data.get('config_reasoning', ''),
                        data.get('current_round', 0),
                        data.get('twitter_status', 'not_started'),
                        data.get('reddit_status', 'not_started'),
                        data.get('created_at', ''),
                        data.get('updated_at', ''),
                        data.get('error'),
                    )
                )
                count += 1
            except Exception as e:
                logger.warning(f"Failed to migrate simulation {sim_id}: {e}")
        conn.commit()
        return count

    def _migrate_reports(self) -> int:
        """Migrate reports from meta.json files."""
        reports_dir = os.path.join(Config.UPLOAD_FOLDER, 'reports')
        if not os.path.exists(reports_dir):
            return 0

        count = 0
        conn = self._get_connection()
        for report_id in os.listdir(reports_dir):
            report_path = os.path.join(reports_dir, report_id)
            if not os.path.isdir(report_path):
                continue
            meta_path = os.path.join(report_path, 'meta.json')
            if not os.path.exists(meta_path):
                continue
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                conn.execute(
                    """INSERT OR IGNORE INTO reports
                    (report_id, simulation_id, graph_id, simulation_requirement,
                     status, outline, created_at, completed_at, error)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        data.get('report_id', report_id),
                        data.get('simulation_id', ''),
                        data.get('graph_id', ''),
                        data.get('simulation_requirement', ''),
                        data.get('status', 'pending'),
                        json.dumps(data.get('outline')) if data.get('outline') else None,
                        data.get('created_at', ''),
                        data.get('completed_at', ''),
                        data.get('error'),
                    )
                )
                count += 1
            except Exception as e:
                logger.warning(f"Failed to migrate report {report_id}: {e}")
        conn.commit()
        return count


def get_db() -> Database:
    """Get the Database singleton instance."""
    return Database()
