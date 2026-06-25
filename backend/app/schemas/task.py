"""
Pydantic models for tasks.

A single source of truth for the Task shape that both the Gemini response
parser and the API response serializer rely on. Using enums for priority
and status means invalid values are rejected at the schema boundary
rather than silently flowing into the frontend.
"""

import uuid
from enum import Enum

from pydantic import BaseModel, Field


class Priority(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task: str
    owner: str = "Unassigned"
    deadline: str = "No deadline"
    priority: Priority = Priority.MEDIUM
    status: TaskStatus = TaskStatus.TODO
