"""
Request and response models for the extraction endpoints.
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.task import Evidence, Task


class ExtractRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Raw meeting notes or transcript text")
    title: Optional[str] = Field(default=None, description="Optional meeting title")
    meeting_date: Optional[str] = Field(
        default=None, alias="meetingDate", description="ISO date used to resolve relative deadlines"
    )
    persist: bool = Field(default=True, description="Store the meeting in cross-meeting memory")

    model_config = ConfigDict(populate_by_name=True)


class Decision(BaseModel):
    text: str
    evidence: Optional[Evidence] = None


class Summary(BaseModel):
    executive_summary: str = Field(..., alias="executiveSummary")
    key_decisions: List[str] = Field(default_factory=list, alias="keyDecisions")
    decisions: List[Decision] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class TraceStep(BaseModel):
    step: str
    duration_ms: float = Field(..., alias="durationMs")
    detail: str = ""

    model_config = {"populate_by_name": True}


class ExtractResponse(BaseModel):
    summary: Summary
    tasks: List[Task]
    meeting_id: Optional[str] = Field(default=None, alias="meetingId")
    warnings: List[str] = Field(default_factory=list)
    trace: List[TraceStep] = Field(default_factory=list)

    model_config = {"populate_by_name": True}
