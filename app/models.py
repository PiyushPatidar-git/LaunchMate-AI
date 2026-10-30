from datetime import datetime
from sqlalchemy import String, Text, Boolean, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

def now(): return datetime.utcnow()

class Profile(Base):
    __tablename__ = "profile"
    id: Mapped[int] = mapped_column(primary_key=True)
    nickname: Mapped[str] = mapped_column(String(80), default="")
    skills: Mapped[str] = mapped_column(Text, default="")
    interests: Mapped[str] = mapped_column(Text, default="")
    goals: Mapped[str] = mapped_column(Text, default="")
    experience: Mapped[str] = mapped_column(Text, default="")

class Opportunity(Base):
    __tablename__ = "opportunities"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    url: Mapped[str] = mapped_column(String(1000))
    url_norm: Mapped[str] = mapped_column(String(1000), unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(40), default="other")
    snippet: Mapped[str] = mapped_column(Text, default="")
    published: Mapped[str] = mapped_column(String(40), default="")
    deadline: Mapped[str] = mapped_column(String(20), default="")
    researched_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    score: Mapped[float] = mapped_column(Float, default=0)
    breakdown: Mapped[str] = mapped_column(Text, default="{}")
    analysis: Mapped[str] = mapped_column(Text, default="")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="new")

class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    opportunity_id: Mapped[int | None] = mapped_column(ForeignKey("opportunities.id", ondelete="SET NULL"), nullable=True)
    priority: Mapped[str] = mapped_column(String(10), default="medium")
    due: Mapped[str] = mapped_column(String(20), default="")
    status: Mapped[str] = mapped_column(String(20), default="todo")

class Document(Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("opportunities.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    mode: Mapped[str] = mapped_column(String(20), default="demo")
    created: Mapped[datetime] = mapped_column(DateTime, default=now)

class Activity(Base):
    __tablename__ = "activity"
    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime, default=now)
    kind: Mapped[str] = mapped_column(String(40))
    message: Mapped[str] = mapped_column(Text)

class Run(Base):
    __tablename__ = "runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime, default=now)
    query: Mapped[str] = mapped_column(Text)
    stages: Mapped[str] = mapped_column(Text, default="[]")
    ok: Mapped[bool] = mapped_column(Boolean, default=False)
