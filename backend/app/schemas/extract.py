"""
Request and response models for /api/extract and /api/extract/upload.
"""

from typing import List

from pydantic import BaseModel, Field

from app.schemas.task import Task


class ExtractRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Raw meeting notes or transcript text")


class Summary(BaseModel):
    executive_summary: str = Field(..., alias="executiveSummary")
    key_decisions: List[str] = Field(default_factory=list, alias="keyDecisions")

    model_config = {"populate_by_name": True}


class ExtractResponse(BaseModel):
    summary: Summary
    tasks: List[Task]
