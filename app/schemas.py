from typing import Literal
from pydantic import BaseModel, Field

class ProfileIn(BaseModel):
    nickname: str = Field("", max_length=80)
    skills: str = Field("", max_length=2000)
    interests: str = Field("", max_length=2000)
    goals: str = Field("", max_length=2000)
    experience: str = Field("", max_length=2000)

class ResearchIn(BaseModel):
    kind: Literal["hackathon", "internship", "scholarship", "other"] = "hackathon"
    keywords: str = Field("", max_length=500)
    skills: str = Field("", max_length=500)
    location: str = Field("", max_length=100)
    mode: Literal["any", "online", "in-person"] = "any"
    deadline_pref: str = Field("", max_length=100)
    goal: str = Field("", max_length=500)

class TaskIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    opportunity_id: int | None = None
    priority: Literal["low", "medium", "high"] = "medium"
    due: str = Field("", pattern=r"^(\d{4}-\d{2}-\d{2})?$")
    status: Literal["todo", "doing", "done"] = "todo"

class StatusIn(BaseModel):
    status: Literal["new", "saved", "dismissed"]

class DeadlineIn(BaseModel):
    deadline: str = Field("", pattern=r"^(\d{4}-\d{2}-\d{2})?$")
    verified: bool = False

class DocIn(BaseModel):
    content: str = Field(..., max_length=50000)

class ClearIn(BaseModel):
    confirm: str
