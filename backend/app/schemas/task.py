"""
Pydantic models for tasks.

A single source of truth for the Task shape that both the pipeline and the
API response serializer rely on. Every task carries the transcript quote it
was derived from (``evidence``) plus the result of verifying that quote, so
the UI and the eval harness can tell grounded items from hallucinated ones.
"""

import uuid
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class Priority(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class Evidence(BaseModel):
    """Where in the transcript an item came from."""

    quote: str = ""
    start: int = -1  # character offsets into the (cleaned) transcript; -1 = not found
    end: int = -1
    score: float = 0.0  # 1.0 = exact match, lower = fuzzy
    verified: bool = False


class Task(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task: str
    owner: str = "Unassigned"
    deadline: str = "No deadline"
    due_date: Optional[str] = Field(default=None, alias="dueDate")  # ISO yyyy-mm-dd when resolvable
    priority: Priority = Priority.MEDIUM
    status: TaskStatus = TaskStatus.TODO
    evidence: Optional[Evidence] = None
    supported: bool = True  # False = flagged by the verifier (possible hallucination)
    confidence: float = 1.0
