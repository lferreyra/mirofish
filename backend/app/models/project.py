"""
Project context management.
Server-side persistent project state, backed by SQLite + file storage for uploads.
"""

import os
import json
import uuid
import shutil
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass, field
from ..config import Config


class ProjectStatus(str, Enum):
    CREATED = "created"
    ONTOLOGY_GENERATED = "ontology_generated"
    GRAPH_BUILDING = "graph_building"
    GRAPH_COMPLETED = "graph_completed"
    FAILED = "failed"


@dataclass
class Project:
    project_id: str
    name: str
    status: ProjectStatus
    created_at: str
    updated_at: str

    files: List[Dict[str, str]] = field(default_factory=list)
    total_text_length: int = 0

    ontology: Optional[Dict[str, Any]] = None
    analysis_summary: Optional[str] = None

    graph_id: Optional[str] = None
    graph_build_task_id: Optional[str] = None

    simulation_requirement: Optional[str] = None
    chunk_size: int = 500
    chunk_overlap: int = 50

    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "status": self.status.value if isinstance(self.status, ProjectStatus) else self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "files": self.files,
            "total_text_length": self.total_text_length,
            "ontology": self.ontology,
            "analysis_summary": self.analysis_summary,
            "graph_id": self.graph_id,
            "graph_build_task_id": self.graph_build_task_id,
            "simulation_requirement": self.simulation_requirement,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "error": self.error
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Project':
        status = data.get('status', 'created')
        if isinstance(status, str):
            status = ProjectStatus(status)

        return cls(
            project_id=data['project_id'],
            name=data.get('name', 'Unnamed Project'),
            status=status,
            created_at=data.get('created_at', ''),
            updated_at=data.get('updated_at', ''),
            files=data.get('files', []),
            total_text_length=data.get('total_text_length', 0),
            ontology=data.get('ontology'),
            analysis_summary=data.get('analysis_summary'),
            graph_id=data.get('graph_id'),
            graph_build_task_id=data.get('graph_build_task_id'),
            simulation_requirement=data.get('simulation_requirement'),
            chunk_size=data.get('chunk_size', 500),
            chunk_overlap=data.get('chunk_overlap', 50),
            error=data.get('error')
        )

    @classmethod
    def from_row(cls, row) -> 'Project':
        """Create Project from a sqlite3.Row."""
        ontology = None
        if row['ontology']:
            try:
                ontology = json.loads(row['ontology'])
            except (json.JSONDecodeError, TypeError):
                pass

        files = []
        if row['files']:
            try:
                files = json.loads(row['files'])
            except (json.JSONDecodeError, TypeError):
                pass

        return cls(
            project_id=row['project_id'],
            name=row['name'],
            status=ProjectStatus(row['status']),
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            files=files,
            total_text_length=row['total_text_length'] or 0,
            ontology=ontology,
            analysis_summary=row['analysis_summary'],
            graph_id=row['graph_id'],
            graph_build_task_id=row['graph_build_task_id'],
            simulation_requirement=row['simulation_requirement'],
            chunk_size=row['chunk_size'] or 500,
            chunk_overlap=row['chunk_overlap'] or 50,
            error=row['error']
        )


class ProjectManager:
    """Project manager - SQLite-backed persistence with file storage for uploads."""

    PROJECTS_DIR = os.path.join(Config.UPLOAD_FOLDER, 'projects')

    @classmethod
    def _get_db(cls):
        from ..database import get_db
        return get_db()

    @classmethod
    def _ensure_projects_dir(cls):
        os.makedirs(cls.PROJECTS_DIR, exist_ok=True)

    @classmethod
    def _get_project_dir(cls, project_id: str) -> str:
        return os.path.join(cls.PROJECTS_DIR, project_id)

    @classmethod
    def _get_project_meta_path(cls, project_id: str) -> str:
        return os.path.join(cls._get_project_dir(project_id), 'project.json')

    @classmethod
    def _get_project_files_dir(cls, project_id: str) -> str:
        return os.path.join(cls._get_project_dir(project_id), 'files')

    @classmethod
    def _get_project_text_path(cls, project_id: str) -> str:
        return os.path.join(cls._get_project_dir(project_id), 'extracted_text.txt')

    @classmethod
    def create_project(cls, name: str = "Unnamed Project") -> Project:
        cls._ensure_projects_dir()

        project_id = f"proj_{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()

        project = Project(
            project_id=project_id,
            name=name,
            status=ProjectStatus.CREATED,
            created_at=now,
            updated_at=now
        )

        # Create directory structure for files
        project_dir = cls._get_project_dir(project_id)
        files_dir = cls._get_project_files_dir(project_id)
        os.makedirs(project_dir, exist_ok=True)
        os.makedirs(files_dir, exist_ok=True)

        # Save to database
        cls.save_project(project)

        return project

    @classmethod
    def save_project(cls, project: Project) -> None:
        """Save project metadata to SQLite (and project.json for backwards compat)."""
        project.updated_at = datetime.now().isoformat()

        db = cls._get_db()
        db.execute(
            """INSERT OR REPLACE INTO projects
            (project_id, name, status, created_at, updated_at,
             total_text_length, ontology, analysis_summary, graph_id,
             graph_build_task_id, simulation_requirement, chunk_size,
             chunk_overlap, error, files)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                project.project_id,
                project.name,
                project.status.value if isinstance(project.status, ProjectStatus) else project.status,
                project.created_at,
                project.updated_at,
                project.total_text_length,
                json.dumps(project.ontology, ensure_ascii=False) if project.ontology else None,
                project.analysis_summary,
                project.graph_id,
                project.graph_build_task_id,
                project.simulation_requirement,
                project.chunk_size,
                project.chunk_overlap,
                project.error,
                json.dumps(project.files, ensure_ascii=False),
            )
        )

        # Also write project.json for backwards compatibility
        meta_path = cls._get_project_meta_path(project.project_id)
        project_dir = os.path.dirname(meta_path)
        if os.path.exists(project_dir):
            try:
                with open(meta_path, 'w', encoding='utf-8') as f:
                    json.dump(project.to_dict(), f, ensure_ascii=False, indent=2)
            except OSError:
                pass

    @classmethod
    def get_project(cls, project_id: str) -> Optional[Project]:
        """Get project from DB, with fallback to file."""
        db = cls._get_db()
        row = db.fetchone("SELECT * FROM projects WHERE project_id = ?", (project_id,))
        if row:
            return Project.from_row(row)

        # Fallback: try loading from project.json
        meta_path = cls._get_project_meta_path(project_id)
        if not os.path.exists(meta_path):
            return None

        with open(meta_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        project = Project.from_dict(data)
        # Migrate to DB for next time
        cls.save_project(project)
        return project

    @classmethod
    def list_projects(cls, limit: int = 50) -> List[Project]:
        db = cls._get_db()
        rows = db.fetchall(
            "SELECT * FROM projects ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        return [Project.from_row(row) for row in rows]

    @classmethod
    def delete_project(cls, project_id: str) -> bool:
        # Delete from DB
        db = cls._get_db()
        db.execute("DELETE FROM projects WHERE project_id = ?", (project_id,))

        # Delete files
        project_dir = cls._get_project_dir(project_id)
        if os.path.exists(project_dir):
            shutil.rmtree(project_dir)
            return True
        return True

    @classmethod
    def save_file_to_project(cls, project_id: str, file_storage, original_filename: str) -> Dict[str, str]:
        files_dir = cls._get_project_files_dir(project_id)
        os.makedirs(files_dir, exist_ok=True)

        ext = os.path.splitext(original_filename)[1].lower()
        safe_filename = f"{uuid.uuid4().hex[:8]}{ext}"
        file_path = os.path.join(files_dir, safe_filename)

        file_storage.save(file_path)
        file_size = os.path.getsize(file_path)

        return {
            "original_filename": original_filename,
            "saved_filename": safe_filename,
            "path": file_path,
            "size": file_size
        }

    @classmethod
    def save_extracted_text(cls, project_id: str, text: str) -> None:
        text_path = cls._get_project_text_path(project_id)
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(text)

    @classmethod
    def get_extracted_text(cls, project_id: str) -> Optional[str]:
        text_path = cls._get_project_text_path(project_id)
        if not os.path.exists(text_path):
            return None
        with open(text_path, 'r', encoding='utf-8') as f:
            return f.read()

    @classmethod
    def get_project_files(cls, project_id: str) -> List[str]:
        files_dir = cls._get_project_files_dir(project_id)
        if not os.path.exists(files_dir):
            return []
        return [
            os.path.join(files_dir, f)
            for f in os.listdir(files_dir)
            if os.path.isfile(os.path.join(files_dir, f))
        ]
